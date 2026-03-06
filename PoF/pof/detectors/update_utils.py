"""Utility functions for automatic database updates."""

import hashlib
import os
import threading
import time
import urllib.request
import urllib.error
from typing import Callable, Optional


def background_binary_update_check(
    file_path: str,
    update_url: str,
    update_interval_days: int = 7,
    on_update_callback: Optional[Callable] = None,
) -> None:
    """Check for updates to a binary file in the background.

    Args:
        file_path: Path to the local file
        update_url: URL to download updates from
        update_interval_days: How often to check for updates (in days)
        on_update_callback: Function to call after successful update
    """

    def update_worker():
        try:
            if not _should_update_binary_file(file_path, update_interval_days):
                return

            print(f"Checking for updates to {file_path}")

            temp_file = file_path + ".tmp"

            try:
                with urllib.request.urlopen(update_url, timeout=30) as response:
                    if response.status == 200:
                        with open(temp_file, "wb") as f:
                            while True:
                                chunk = response.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)

                        if _files_are_different(file_path, temp_file):
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            os.rename(temp_file, file_path)

                            print(f"Updated {file_path}")

                            if on_update_callback:
                                on_update_callback()
                        else:
                            os.remove(temp_file)
                            print(f"No update needed for {file_path}")
                    else:
                        print(f"Failed to download update: HTTP {response.status}")

            except urllib.error.URLError as e:
                print(f"Failed to download update: {e}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Error during update: {e}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        except Exception as e:
            print(f"Background update error: {e}")

    thread = threading.Thread(target=update_worker, daemon=True)
    thread.start()


def _should_update_binary_file(file_path: str, update_interval_days: int) -> bool:
    """Check if a binary file should be updated based on age.

    Args:
        file_path: Path to the file
        update_interval_days: Update interval in days

    Returns:
        True if the file should be updated
    """
    if not os.path.exists(file_path):
        return True

    file_age = time.time() - os.path.getmtime(file_path)
    max_age = update_interval_days * 24 * 3600

    return file_age > max_age


def _files_are_different(file1: str, file2: str) -> bool:
    """Check if two files are different by comparing their hashes.

    Args:
        file1: Path to first file
        file2: Path to second file

    Returns:
        True if files are different
    """
    if not os.path.exists(file1):
        return True

    if not os.path.exists(file2):
        return False

    if os.path.getsize(file1) != os.path.getsize(file2):
        return True

    hash1 = _get_file_hash(file1)
    hash2 = _get_file_hash(file2)

    return hash1 != hash2


def _get_file_hash(file_path: str) -> str:
    """Get SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        SHA256 hash as hex string
    """
    hash_sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()
