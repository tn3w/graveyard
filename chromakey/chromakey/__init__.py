import time
import secrets
import jwt
import os
import hashlib
import logging
from functools import update_wrapper
from flask import (
    Blueprint,
    request,
    jsonify,
    redirect,
    render_template,
    make_response,
    current_app,
)

logger = logging.getLogger(__name__)

CHROMAKEY_EVALUATED = "_CHROMAKEY_EVALUATED"

DEFAULT_OPTIONS = {
    "secret_key": None,
    "require_auth": False,
    "inject_overlay": True,
    "token_expiry": 3600,
    "cookie_secure": None,
    "max_attempts": 5,
    "lockout_duration": 300,
    "challenge_expiry": 30,
    "token_redirect_home": False,
}


def get_chromakey_options(app_instance, *dicts):
    options: dict = DEFAULT_OPTIONS.copy()
    options.update(get_app_kwarg_dict(app_instance))
    if dicts:
        for d in dicts:
            if d:
                options.update(d)

    if not options.get("secret_key"):
        secret_key = os.environ.get("CHROMAKEY_SECRET_KEY")
        if not secret_key:
            raise ValueError(
                "CHROMAKEY_SECRET_KEY must be set. "
                "Generate: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        options["secret_key"] = secret_key

    return options


def get_app_kwarg_dict(app_instance=None):
    app = app_instance or current_app
    app_config = getattr(app, "config", {})
    config_options = [
        "CHROMAKEY_SECRET_KEY",
        "CHROMAKEY_REQUIRE_AUTH",
        "CHROMAKEY_INJECT_OVERLAY",
        "CHROMAKEY_TOKEN_EXPIRY",
        "CHROMAKEY_TOKEN_REDIRECT_HOME",
    ]
    return {
        k.lower().replace("chromakey_", ""): app_config.get(k)
        for k in config_options
        if app_config.get(k) is not None
    }


def generate_jwt_token(secret_key, expiry):
    return jwt.encode(
        {"auth": True, "exp": int(time.time()) + expiry},
        secret_key,
        algorithm="HS256",
    )


def verify_jwt_token(token, secret_key, session_revocations):
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        session_token = payload.get("sid")

        if session_token and session_token in session_revocations:
            return False

        return payload.get("auth", False)
    except jwt.InvalidTokenError:
        return False


def check_authentication(secret_key, session_revocations=None):
    token = request.cookies.get("chromakey")
    if token:
        if session_revocations is None:
            session_revocations = set()
        return verify_jwt_token(token, secret_key, session_revocations)
    return False


def inject_overlay_html(response):
    if not response.content_type or "text/html" not in response.content_type:
        return response
    if request.path.startswith("/chromakey"):
        return response

    data = response.get_data(as_text=True)
    overlay = render_template("overlay.html")

    for tag in ("</body>", "</html>"):
        if tag in data:
            response.set_data(data.replace(tag, overlay + tag))
            break

    return response


def generate_challenge():
    shapes = ["circle", "square", "triangle", "star", "heart", "diamond"]
    colors = ["red", "blue", "green", "yellow", "purple"]

    result = [
        {"shape": secrets.choice(shapes), "color": secrets.choice(colors)}
        for _ in range(4)
    ]

    return result


VALID_SHAPES = {"circle", "square", "triangle", "star", "heart", "diamond"}
VALID_COLORS = {"red", "blue", "green", "yellow", "purple"}


def verify_challenge(user_input, expected_challenge):
    if not isinstance(user_input, list) or not isinstance(expected_challenge, list):
        return False

    if len(user_input) != 4 or len(expected_challenge) != 4:
        return False

    for item in user_input:
        if not isinstance(item, dict):
            return False
        if "shape" not in item or "color" not in item:
            return False
        if item["shape"] not in VALID_SHAPES or item["color"] not in VALID_COLORS:
            return False

    result = True
    for i in range(4):
        shape_match = secrets.compare_digest(
            user_input[i]["shape"], expected_challenge[i]["shape"]
        )
        color_match = secrets.compare_digest(
            user_input[i]["color"], expected_challenge[i]["color"]
        )
        result = result and shape_match and color_match

    return result


def chromakey(*args, **kwargs):
    _options = kwargs

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            options = get_chromakey_options(current_app, _options)

            if not check_authentication(options["secret_key"]):
                return redirect(f"/chromakey/login?next={request.path}")

            resp = make_response(f(*args, **kwargs))

            if options.get("inject_overlay"):
                resp = inject_overlay_html(resp)

            setattr(resp, CHROMAKEY_EVALUATED, True)
            return resp

        return update_wrapper(wrapped_function, f)

    return decorator


class Chromakey:
    def __init__(self, app=None, **kwargs):
        self._options = kwargs
        if app is not None:
            self.init_app(app, **kwargs)

    def init_app(self, app, **kwargs):
        options = get_chromakey_options(app, self._options, kwargs)
        secret_key = options["secret_key"]
        auth_password_hash = os.environ.get("CHROMAKEY_AUTH_PASSWORD")
        if not auth_password_hash:
            raise ValueError("CHROMAKEY_AUTH_PASSWORD must be set (as SHA256 hash)")

        blueprint = create_chromakey_blueprint(secret_key, options, auth_password_hash)
        app.register_blueprint(blueprint)

        if options.get("inject_overlay"):
            app.after_request(make_after_request_function())

        if options.get("require_auth"):
            app.before_request(make_before_request_function(secret_key))

        if app.debug:
            logger.warning(
                "Chromakey initialized in DEBUG mode - "
                "use CHROMAKEY_AUTH_PASSWORD to authenticate"
            )
        else:
            logger.info("Chromakey authentication initialized")


def create_chromakey_blueprint(secret_key, options, auth_password_hash):
    blueprint = Blueprint("chromakey", __name__, url_prefix="/chromakey")
    token_expiry = options.get("token_expiry", 3600)
    max_attempts = options.get("max_attempts", 5)
    lockout_duration = options.get("lockout_duration", 300)
    challenge_expiry = options.get("challenge_expiry", 30)

    failed_attempts = {}
    session_revocations = set()
    global_attempts = []
    current_challenge = {"data": None, "expires_at": 0}

    def get_cookie_secure_flag():
        if options.get("cookie_secure") is not None:
            return options["cookie_secure"]

        app = current_app
        if app.debug:
            logger.warning(
                "DEBUG mode - cookies without 'secure' flag. "
                "INSECURE for production!"
            )
            return False
        return True

    def is_safe_redirect_url(target):
        if not target:
            return False

        from urllib.parse import urlparse

        try:
            parsed = urlparse(target)
            return not parsed.netloc and parsed.path.startswith("/")
        except Exception:
            return False

    def get_safe_redirect():
        next_url = request.args.get("next") or request.form.get("next")
        if next_url and is_safe_redirect_url(next_url):
            return next_url
        return "/"

    def get_current_challenge():
        now = time.time()
        if not current_challenge["data"] or now >= current_challenge["expires_at"]:
            current_challenge["data"] = generate_challenge()
            current_challenge["expires_at"] = now + challenge_expiry
        return current_challenge["data"]

    def generate_csrf_token():
        timestamp = int(time.time())
        nonce = secrets.token_urlsafe(32)

        token = jwt.encode(
            {"ts": timestamp, "nonce": nonce},
            secret_key,
            algorithm="HS256",
        )
        return token

    def verify_csrf_token(token):
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])

            token_age = time.time() - payload.get("ts", 0)
            if token_age > 300 or token_age < 0:
                return False

            return True
        except jwt.InvalidTokenError:
            return False

    @blueprint.route("/challenge", methods=["GET"])
    def get_challenge():
        if not check_authentication(secret_key, session_revocations):
            return jsonify({"error": "Unauthorized"}), 401

        challenge_data = get_current_challenge()

        response = jsonify(
            {
                "challenge": challenge_data,
                "expires_at": current_challenge["expires_at"],
            }
        )
        return response

    @blueprint.route("/verify", methods=["POST"])
    def verify():
        client_ip = request.remote_addr
        now = time.time()

        global_attempts[:] = [t for t in global_attempts if now - t < 60]
        if len(global_attempts) >= 50:
            logger.warning("Global rate limit")
            return jsonify({"authorized": False}), 503

        if client_ip in failed_attempts:
            failed_attempts[client_ip] = [
                t for t in failed_attempts[client_ip] if now - t < lockout_duration
            ]

            recent = sum(1 for t in failed_attempts[client_ip] if now - t < 60)
            if recent >= max_attempts:
                logger.warning(f"Rate limit for IP {client_ip}")
                return jsonify({"authorized": False, "error": "Too many attempts"}), 429

        if request.content_type != "application/json":
            return jsonify({"authorized": False}), 400

        try:
            data = request.get_json(force=False, silent=False)
        except Exception:
            return jsonify({"authorized": False}), 400

        if not data or "selection" not in data:
            return jsonify({"authorized": False}), 400

        csrf_token = request.cookies.get("chromakey_csrf")
        if not csrf_token or not verify_csrf_token(csrf_token):
            logger.warning(f"Invalid CSRF from IP {client_ip}")
            return jsonify({"authorized": False}), 403

        expected_challenge = get_current_challenge()

        if now >= current_challenge["expires_at"]:
            return jsonify({"authorized": False}), 403

        global_attempts.append(now)

        next_url = data.get("next", "")
        if next_url and not is_safe_redirect_url(next_url):
            next_url = "/"

        if verify_challenge(data["selection"], expected_challenge):
            failed_attempts.pop(client_ip, None)

            session_token = secrets.token_urlsafe(32)
            token = jwt.encode(
                {
                    "auth": True,
                    "exp": int(time.time()) + token_expiry,
                    "sid": session_token,
                },
                secret_key,
                algorithm="HS256",
            )

            redirect_url = next_url if next_url else "/"
            response = jsonify({"authorized": True, "redirect": redirect_url})
            response.set_cookie(
                "chromakey",
                token,
                max_age=token_expiry,
                httponly=True,
                secure=get_cookie_secure_flag(),
                samesite="Strict",
            )
            response.delete_cookie("chromakey_csrf")

            logger.info(f"Auth success from IP {client_ip}")
            return response

        if client_ip not in failed_attempts:
            failed_attempts[client_ip] = []
        failed_attempts[client_ip].append(now)

        logger.warning(f"Failed auth from IP {client_ip}")

        return jsonify({"authorized": False})

    @blueprint.route("/challenge/<challenge_code>")
    def challenge_auth(challenge_code):
        client_ip = request.remote_addr
        now = time.time()

        expected_challenge = get_current_challenge()

        if now >= current_challenge["expires_at"]:
            logger.warning(f"Expired challenge from IP {client_ip}")
            return redirect("/chromakey/login")

        shape_code_map = {
            "C": "circle",
            "S": "square",
            "T": "triangle",
            "A": "star",
            "H": "heart",
            "D": "diamond",
        }
        color_code_map = {
            "R": "red",
            "B": "blue",
            "G": "green",
            "Y": "yellow",
            "P": "purple",
        }

        cleaned = challenge_code.upper().replace(" ", "")
        if len(cleaned) != 8:
            logger.warning(f"Invalid challenge length from IP {client_ip}")
            return redirect("/chromakey/login")

        user_selection = []
        for i in range(0, 8, 2):
            shape = shape_code_map.get(cleaned[i])
            color = color_code_map.get(cleaned[i + 1])
            if not shape or not color:
                logger.warning(f"Invalid challenge code from IP {client_ip}")
                return redirect("/chromakey/login")
            user_selection.append({"shape": shape, "color": color})

        if not verify_challenge(user_selection, expected_challenge):
            logger.warning(f"Failed challenge auth from IP {client_ip}")
            return redirect("/chromakey/login")

        session_token = secrets.token_urlsafe(32)
        jwt_token = jwt.encode(
            {
                "auth": True,
                "exp": int(time.time()) + token_expiry,
                "sid": session_token,
            },
            secret_key,
            algorithm="HS256",
        )

        next_url = request.args.get("next", "/")
        if not is_safe_redirect_url(next_url):
            next_url = "/"

        response = make_response(redirect(next_url))
        response.set_cookie(
            "chromakey",
            jwt_token,
            max_age=token_expiry,
            httponly=True,
            secure=get_cookie_secure_flag(),
            samesite="Strict",
        )

        logger.info(f"Challenge auth success from IP {client_ip}")
        return response

    @blueprint.route("/<token>")
    def token_auth(token):
        provided_hash = hashlib.sha256(token.encode()).hexdigest()

        if not secrets.compare_digest(provided_hash, auth_password_hash):
            logger.warning(f"Invalid token from IP {request.remote_addr}")
            return redirect("/")

        session_token = secrets.token_urlsafe(32)
        jwt_token = jwt.encode(
            {
                "auth": True,
                "exp": int(time.time()) + token_expiry,
                "sid": session_token,
            },
            secret_key,
            algorithm="HS256",
        )

        if options.get("token_redirect_home"):
            response = make_response(redirect("/"))
        else:
            response = make_response(render_template("overlay.html", fullscreen=True))
        
        response.set_cookie(
            "chromakey",
            jwt_token,
            max_age=token_expiry,
            httponly=True,
            secure=get_cookie_secure_flag(),
            samesite="Strict",
        )

        logger.info(f"Token auth from IP {request.remote_addr}")
        return response

    @blueprint.route("/login")
    def login_page():
        if check_authentication(secret_key, session_revocations):
            return redirect(get_safe_redirect())

        csrf_token = generate_csrf_token()
        next_url = request.args.get("next", "")

        response = make_response(render_template("login.html", next_url=next_url))
        response.set_cookie(
            "chromakey_csrf",
            csrf_token,
            max_age=300,
            httponly=True,
            secure=get_cookie_secure_flag(),
            samesite="Strict",
        )
        return response

    @blueprint.route("/logout", methods=["POST"])
    def logout():
        token = request.cookies.get("chromakey")
        if token:
            try:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                session_token = payload.get("sid")
                if session_token:
                    session_revocations.add(session_token)
            except jwt.InvalidTokenError:
                pass

        response = jsonify({"success": True})
        response.delete_cookie("chromakey")
        response.delete_cookie("chromakey_csrf")

        logger.info(f"Logout from IP {request.remote_addr}")
        return response

    return blueprint


def make_after_request_function():
    def chromakey_after_request(response):
        if hasattr(response, CHROMAKEY_EVALUATED):
            return response

        if getattr(request, "authenticated", False):
            return inject_overlay_html(response)

        return response

    return chromakey_after_request


def make_before_request_function(secret_key):
    def chromakey_before_request():
        if request.path.startswith(("/chromakey", "/static")):
            setattr(request, "authenticated", True)
            return

        if check_authentication(secret_key, set()):
            setattr(request, "authenticated", True)
            return

        setattr(request, "authenticated", False)
        if request.method == "GET":
            return redirect(f"/chromakey/login?next={request.path}")
        return jsonify({"error": "Authentication required"}), 401

    return chromakey_before_request


__all__ = ["Chromakey", "chromakey"]
