"""IP2Location database based bot detection."""

import os
import threading
from dataclasses import dataclass
from typing import Optional

try:
    from IP2Proxy import IP2Proxy

    IP2PROXY_AVAILABLE = True
except ImportError:

    class IP2Proxy:
        """Mock IP2Proxy class for missing library."""

        def open(self, _):
            """Open the database."""

        def close(self):
            """Close the database."""

        def get_all(self, _):
            """Get all data for the IP."""
            return {}

    IP2PROXY_AVAILABLE = False

from .base import BaseDetector, BaseResult
from .update_utils import background_binary_update_check


@dataclass
class IP2LocationResult(BaseResult):
    """Result of IP2Location detection."""

    ip: str = ""
    is_proxy: bool = False
    isp: Optional[str] = None
    domain: Optional[str] = None
    fraud_score: Optional[float] = None
    threat_type: Optional[str] = None

    @property
    def is_bot(self) -> bool:
        """Check if the IP indicates bot behavior."""
        return self.is_proxy


class IP2LocationDetector(BaseDetector):
    """Detects bots using IP2Location database."""

    _instance = None
    _lock = threading.Lock()
    _db_loaded = False
    _db_path = "IP2PROXY-LITE-PX12.BIN"
    _update_url = (
        "https://www.ip2location.com/download/?token={api_key}&file=PX12LITEBIN"
    )
    _ip2proxy_db: Optional[IP2Proxy] = None
    _update_checked = False

    def __init__(
        self,
        enabled: bool = True,
        cache_ttl: int = 3600,
        db_path: str = "IP2PROXY-LITE-PX12.BIN",
        api_key: Optional[str] = None,
    ):
        """Initialize the IP2Location detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
            db_path: Path to the IP2Location database file
            api_key: API key for downloading database updates
        """
        super().__init__(enabled, cache_ttl)

        if not IP2PROXY_AVAILABLE:
            print(
                "Warning: IP2Proxy library not available. IP2Location detection disabled."
            )
            self.enabled = False
            return

        self.db_path = db_path
        self.api_key = api_key

        self._ensure_database_loaded()

        if api_key and not IP2LocationDetector._update_checked:
            with IP2LocationDetector._lock:
                if not IP2LocationDetector._update_checked:
                    update_url = IP2LocationDetector._update_url.format(api_key=api_key)
                    background_binary_update_check(
                        self.db_path,
                        update_url,
                        update_interval_days=7,
                        on_update_callback=self._reload_database,
                    )
                    IP2LocationDetector._update_checked = True

    def get_cache_key(self, **kwargs) -> str:
        """Generate cache key for the given parameters."""
        ip = kwargs.get("ip", "")
        return f"ip2location:{ip}"

    def _ensure_database_loaded(self) -> None:
        """Ensure the IP2Location database is loaded."""
        if not IP2PROXY_AVAILABLE:
            return

        with IP2LocationDetector._lock:
            if not IP2LocationDetector._db_loaded:
                if os.path.exists(self.db_path):
                    try:
                        IP2LocationDetector._ip2proxy_db = IP2Proxy()
                        IP2LocationDetector._ip2proxy_db.open(self.db_path)
                        IP2LocationDetector._db_loaded = True
                        print(f"Loaded IP2Location database: {self.db_path}")
                    except Exception as e:
                        print(f"Failed to load IP2Location database: {e}")
                        IP2LocationDetector._ip2proxy_db = None
                else:
                    print(f"IP2Location database not found: {self.db_path}")

    @classmethod
    def _reload_database(cls) -> None:
        """Reload the database after an update."""
        with cls._lock:
            if cls._ip2proxy_db:
                try:
                    cls._ip2proxy_db.close()
                except Exception:
                    pass

            cls._db_loaded = False
            print("IP2Location database marked for reload")

    def detect(self, **kwargs) -> IP2LocationResult:
        """Detect bot behavior based on IP address using IP2Location database.

        Args:
            ip: IP address to check

        Returns:
            IP2LocationResult with detection results
        """
        ip = kwargs.get("ip", "")

        if not ip or not IP2PROXY_AVAILABLE:
            return IP2LocationResult(ip=ip)

        self._ensure_database_loaded()

        if not IP2LocationDetector._ip2proxy_db:
            return IP2LocationResult(ip=ip)

        try:
            result_data = IP2LocationDetector._ip2proxy_db.get_all(ip)

            fraud_score = result_data.get("fraud_score")
            if isinstance(fraud_score, str) and fraud_score.isdigit():
                fraud_score = int(fraud_score)
            else:
                fraud_score = self._calculate_fraud_score(result_data)

            result = IP2LocationResult(
                ip=ip,
                is_proxy=result_data.get("proxy_type") == "1",
                isp=result_data.get("isp") if result_data.get("isp") != "-" else None,
                domain=(
                    result_data.get("domain")
                    if result_data.get("domain") != "-"
                    else None
                ),
                fraud_score=fraud_score,
                threat_type=(
                    result_data.get("threat", "").lower()
                    if isinstance(result_data.get("threat"), str)
                    and result_data.get("threat") != "-"
                    else None
                ),
            )

            return result

        except Exception as e:
            print(f"Error in IP2Location detection: {e}")
            return IP2LocationResult(ip=ip)

    def _calculate_fraud_score(self, result_data: dict) -> Optional[float]:
        """Calculate a fraud score based on the IP2Location data.

        Args:
            result_data: Raw data from IP2Location

        Returns:
            Fraud score between 0.0 and 1.0, or None if cannot calculate
        """
        try:
            score = 0.0

            if result_data.get("proxy_type") == "1":
                score += 0.5

            threat = result_data.get("threat", "").lower()
            if threat and threat != "-":
                threat_scores = {
                    "malware": 0.3,
                    "phishing": 0.3,
                    "spam": 0.2,
                    "bot": 0.4,
                    "scanner": 0.3,
                    "attack": 0.4,
                }

                for threat_type, threat_score in threat_scores.items():
                    if threat_type in threat:
                        score += threat_score
                        break

            return min(score, 1.0) if score > 0 else None

        except Exception:
            return None
