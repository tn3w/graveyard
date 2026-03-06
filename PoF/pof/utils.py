import json
import os
import threading
import time
from typing import Callable, Optional
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from netaddr import IPAddress, AddrFormatError


def is_valid_routable_ip(ip: str) -> bool:
    """Check if the IP address is valid and routable."""
    try:
        ip_obj = IPAddress(ip)

        is_private = (ip_obj.version == 4 and ip_obj.is_ipv4_private_use()) or (
            ip_obj.version == 6 and ip_obj.is_ipv6_unique_local()
        )

        return not (
            is_private
            or ip_obj.is_loopback()
            or ip_obj.is_multicast()
            or ip_obj.is_reserved()
            or ip_obj.is_link_local()
        )
    except (AddrFormatError, ValueError):
        return False


def check_and_update_file(
    file_path: str,
    update_url: str,
    max_age_days: int = 7,
    timeout: int = 30,
    on_update_callback: Optional[Callable[[], None]] = None,
) -> bool:
    """Check if file needs updating and update it if necessary.

    Args:
        file_path: Path to the JSON file to check/update
        update_url: URL to download updates from
        max_age_days: Maximum age in days before update is needed
        timeout: HTTP request timeout in seconds
        on_update_callback: Optional callback to call after successful update

    Returns:
        bool: True if file was updated, False otherwise
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    timestamp = data.get("_timestamp")

                    if timestamp:
                        current_time = time.time()
                        file_age_days = (current_time - timestamp) / (24 * 3600)

                        if file_age_days < max_age_days:
                            return False
                except (json.JSONDecodeError, KeyError):
                    pass

        updated = _download_and_update_file(file_path, update_url, timeout)
        if updated and on_update_callback:
            on_update_callback()
        return updated

    except Exception:
        return False


def _download_and_update_file(file_path: str, update_url: str, timeout: int) -> bool:
    """Download file from URL and update local file with timestamp.

    Args:
        file_path: Path to the local file
        update_url: URL to download from
        timeout: HTTP request timeout in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with urlopen(update_url, timeout=timeout) as response:
            if response.status != 200:
                return False

            data = json.loads(response.read().decode("utf-8"))

        data["_timestamp"] = time.time()

        temp_file = file_path + ".tmp"
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())

        os.rename(temp_file, file_path)
        return True

    except (URLError, HTTPError, json.JSONDecodeError, OSError, IOError):
        temp_file = file_path + ".tmp"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        return False


def background_update_check(
    file_path: str,
    update_url: str,
    max_age_days: int = 7,
    timeout: int = 30,
    on_update_callback: Optional[Callable[[], None]] = None,
) -> None:
    """Perform background update check in a separate thread.

    Args:
        file_path: Path to the JSON file to check/update
        update_url: URL to download updates from
        max_age_days: Maximum age in days before update is needed
        timeout: HTTP request timeout in seconds
        on_update_callback: Optional callback to call after successful update
    """

    def _update_worker():
        try:
            check_and_update_file(
                file_path, update_url, max_age_days, timeout, on_update_callback
            )
        except Exception:
            pass

    thread = threading.Thread(target=_update_worker, daemon=True)
    thread.start()
