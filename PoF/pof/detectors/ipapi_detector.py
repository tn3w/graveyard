"""IP API based bot detection supporting multiple services."""

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .api_base import BaseApiDetector
from .base import BaseResult


@dataclass
class IPApiResult(BaseResult):
    """Result of IP API detection."""

    ip: str = ""
    is_proxy: bool = False
    is_hosting: bool = False
    country: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    service_used: str = "unknown"

    @property
    def is_bot(self) -> bool:
        """Check if the IP indicates bot behavior."""
        return self.is_proxy or self.is_hosting


class IPApiComDetector(BaseApiDetector):
    """Detects bots using IP-API.com service specifically."""

    def __init__(self, enabled: bool = True, cache_ttl: int = 3600, **kwargs):
        """Initialize the IP-API.com detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
            **kwargs: Additional arguments for BaseApiDetector
        """
        super().__init__(enabled, cache_ttl, api_key=None, **kwargs)

        self._min_request_interval = 1.5

    def get_cache_key(self, **kwargs) -> str:
        """Generate cache key for the given parameters."""
        ip = kwargs.get("ip", "")
        return f"ipapicom:{ip}"

    def validate_parameters(self, **kwargs) -> bool:
        """Validate the parameters for the API request.

        Args:
            **kwargs: Parameters to validate

        Returns:
            True if parameters are valid
        """
        ip = kwargs.get("ip", "")
        if not ip:
            return False

        ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"

        if re.match(ipv4_pattern, ip):
            octets = ip.split(".")
            return all(0 <= int(octet) <= 255 for octet in octets)
        if re.match(ipv6_pattern, ip):
            return True
        return "::" in ip or ":" in ip

    def build_request_url(self, **kwargs) -> str:
        """Build the API request URL.

        Args:
            **kwargs: Parameters for the request (must include 'ip')

        Returns:
            Complete API URL
        """
        ip = kwargs.get("ip", "")
        return f"http://ip-api.com/json/{ip}?fields=proxy,hosting,country,isp,org"

    def parse_response(self, response_data: Dict[str, Any], **kwargs) -> IPApiResult:
        """Parse the API response into a result object.

        Args:
            response_data: JSON response from the API
            **kwargs: Original request parameters

        Returns:
            IPApiResult with detection results
        """
        ip = kwargs.get("ip", "")

        result = IPApiResult(ip=ip, service_used="ipapicom")

        result.is_proxy = response_data.get("proxy", False)
        result.is_hosting = response_data.get("hosting", False)
        result.country = response_data.get("country")
        result.isp = response_data.get("isp")
        result.org = response_data.get("org")

        return result


class IPInfoDetector(BaseApiDetector):
    """Detects bots using IPInfo.io service."""

    def __init__(
        self,
        enabled: bool = True,
        cache_ttl: int = 3600,
        ipinfo_token: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the IPInfo detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
            ipinfo_token: API token for ipinfo.io service
            **kwargs: Additional arguments for BaseApiDetector
        """
        super().__init__(enabled, cache_ttl, api_key=ipinfo_token, **kwargs)
        self.ipinfo_token = ipinfo_token

        self._min_request_interval = 0.1

    def get_cache_key(self, **kwargs) -> str:
        """Generate cache key for the given parameters."""
        ip = kwargs.get("ip", "")
        return f"ipinfo:{ip}"

    def validate_parameters(self, **kwargs) -> bool:
        """Validate the parameters for the API request.

        Args:
            **kwargs: Parameters to validate

        Returns:
            True if parameters are valid
        """
        ip = kwargs.get("ip", "")
        if not ip:
            return False

        ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"

        if re.match(ipv4_pattern, ip):
            octets = ip.split(".")
            return all(0 <= int(octet) <= 255 for octet in octets)
        if re.match(ipv6_pattern, ip):
            return True
        return "::" in ip or ":" in ip

    def build_request_url(self, **kwargs) -> str:
        """Build the API request URL.

        Args:
            **kwargs: Parameters for the request (must include 'ip')

        Returns:
            Complete API URL
        """
        ip = kwargs.get("ip", "")
        if self.ipinfo_token:
            return f"https://ipinfo.io/{ip}/json?token={self.ipinfo_token}"
        return f"https://ipinfo.io/{ip}/json"

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for IPInfo.io."""
        if self.ipinfo_token:
            return {"Authorization": f"Bearer {self.ipinfo_token}"}
        return {}

    def parse_response(self, response_data: Dict[str, Any], **kwargs) -> IPApiResult:
        """Parse the API response into a result object.

        Args:
            response_data: JSON response from the API
            **kwargs: Original request parameters

        Returns:
            IPApiResult with detection results
        """
        ip = kwargs.get("ip", "")

        result = IPApiResult(ip=ip, service_used="ipinfo")

        org = response_data.get("org", "").lower()
        hostname = response_data.get("hostname", "").lower()

        hosting_indicators = [
            "amazon",
            "aws",
            "google",
            "microsoft",
            "azure",
            "digitalocean",
            "linode",
            "vultr",
            "ovh",
            "hetzner",
            "cloudflare",
            "fastly",
            "hosting",
            "server",
            "cloud",
            "datacenter",
            "data center",
        ]

        proxy_indicators = [
            "proxy",
            "vpn",
            "tor",
            "anonymous",
            "privacy",
            "hide",
            "tunnel",
            "shield",
            "secure",
        ]

        result.is_hosting = any(
            indicator in org for indicator in hosting_indicators
        ) or any(indicator in hostname for indicator in hosting_indicators)
        result.is_proxy = any(
            indicator in org for indicator in proxy_indicators
        ) or any(indicator in hostname for indicator in proxy_indicators)

        result.country = response_data.get("country")
        result.isp = response_data.get("org")
        result.org = response_data.get("org")

        return result
