"""IPSet based bot detection using the existing IPSet functionality."""

from dataclasses import dataclass
from typing import List, Optional

from .base import BaseDetector, BaseResult
from ..ipset import IPSet, IPSetResult as OriginalIPSetResult
from ..utils import is_valid_routable_ip


@dataclass
class IPSetResult(BaseResult):
    """Result of IPSet detection."""

    ip: str = ""
    is_vpn: bool = False
    vpn_provider: Optional[str] = None
    is_proxy: bool = False
    is_datacenter: bool = False
    is_forum_spammer: bool = False
    is_firehol: bool = False
    is_tor_exit_node: bool = False
    is_other_group: bool = False
    is_invalid_ip: bool = False
    groups: List[str] | None = None

    def __post_init__(self):
        super().__post_init__()
        if self.groups is None:
            self.groups = []

    @property
    def is_bot(self) -> bool:
        """Check if the IP indicates bot behavior."""
        return (
            self.is_invalid_ip
            or self.is_vpn
            or self.is_proxy
            or self.is_datacenter
            or self.is_forum_spammer
            or self.is_firehol
            or self.is_tor_exit_node
            or self.is_other_group
        )

    @classmethod
    def from_original_result(cls, original: OriginalIPSetResult) -> "IPSetResult":
        """Convert from the original IPSetResult to the new format.

        Args:
            original: Original IPSetResult instance

        Returns:
            New IPSetResult instance
        """
        return cls(
            ip=original.ip or "",
            is_vpn=original.is_vpn,
            vpn_provider=original.vpn_provider,
            is_proxy=original.is_proxy,
            is_datacenter=original.is_datacenter,
            is_forum_spammer=original.is_forum_spammer,
            is_firehol=original.is_firehol,
            is_tor_exit_node=original.is_tor_exit_node,
            is_other_group=original.is_other_group,
            is_invalid_ip=original.is_invalid_ip,
        )


class IPSetDetector(BaseDetector):
    """Detects bots using IPSet data."""

    def __init__(
        self,
        enabled: bool = True,
        cache_ttl: int = 3600,
        ipset_file: str = "ipset.json",
    ):
        """Initialize the IPSet detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
            ipset_file: Path to the IPSet JSON file
        """
        super().__init__(enabled, cache_ttl)
        self.ipset_file = ipset_file
        self._ipset: Optional[IPSet] = None

    @property
    def ipset(self) -> IPSet:
        """Get the IPSet instance, creating it if necessary."""
        if self._ipset is None:
            self._ipset = IPSet(self.ipset_file)
        return self._ipset

    def get_cache_key(self, **kwargs) -> str:
        """Generate cache key for the given parameters."""
        ip = kwargs.get("ip", "")
        return f"ipset:{ip}"

    def detect(self, **kwargs) -> IPSetResult:
        """Detect bot behavior based on IP address.

        Args:
            ip: IP address to check

        Returns:
            IPSetResult with detection results
        """
        ip = kwargs.get("ip", "")

        if not ip:
            return IPSetResult(ip=ip, is_invalid_ip=True)

        if not is_valid_routable_ip(ip):
            return IPSetResult(ip=ip, is_invalid_ip=True)

        groups = self.ipset.get_groups(ip)

        original_result = OriginalIPSetResult.from_ip_groups(ip, groups)

        result = IPSetResult.from_original_result(original_result)
        result.groups = groups

        return result
