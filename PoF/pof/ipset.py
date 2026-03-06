"""Fast IP group lookup module.

Provides optimized IP address to group mapping
using pre-computed integer ranges and binary search.
"""

import json
import os
import socket
import struct
import threading
from dataclasses import dataclass
from typing import Dict, List, Tuple

from netaddr import IPNetwork

from .utils import background_update_check


VPN_PROVIDERS = [
    "NordVPN",
    "ProtonVPN",
    "ExpressVPN",
    "Surfshark",
    "PrivateInternetAccess",
    "CyberGhost",
    "TunnelBear",
    "Mullvad",
]


ALL_GROUPS = [
    *VPN_PROVIDERS,
    "FireholProxies",
    "AwesomeProxies",
    "Datacenter",
    "StopForumSpam",
    "FireholLevel1",
    "TorExitNodes",
]


@dataclass
class IPSetResult:
    """Result of IP group lookup."""

    ip: str | None = None
    is_vpn: bool = False
    vpn_provider: str | None = None
    is_proxy: bool = False
    is_datacenter: bool = False
    is_forum_spammer: bool = False
    is_firehol: bool = False
    is_tor_exit_node: bool = False
    is_other_group: bool = False
    is_invalid_ip: bool = False

    @property
    def is_bot(self) -> bool:
        """Check if the IP is a bot."""
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
    def from_ip_groups(cls, ip: str, ip_groups: List[str]) -> "IPSetResult":
        """
        Create a IPSetResult from a list of IP groups.
        """
        vpn_provider = next((name for name in VPN_PROVIDERS if name in ip_groups), None)

        result = IPSetResult(
            ip=ip,
            is_vpn=vpn_provider is not None,
            vpn_provider=vpn_provider,
            is_proxy="FireholProxies" in ip_groups or "AwesomeProxies" in ip_groups,
            is_datacenter="Datacenter" in ip_groups,
            is_forum_spammer="StopForumSpam" in ip_groups,
            is_firehol="FireholLevel1" in ip_groups,
            is_tor_exit_node="TorExitNodes" in ip_groups,
            is_other_group=any(group not in ALL_GROUPS for group in ip_groups),
        )
        return result


class IPSet:
    """Fast IP group lookup with thread-safe singleton loading."""

    _instance = None
    _lock = threading.Lock()
    _data_loaded = False
    _file_path = "ipset.json"
    _update_url = (
        "https://raw.githubusercontent.com/tn3w/IPSet/refs/heads/master/ipset.json"
    )
    _ip_to_groups: Dict[str, List[str]] = {}
    _ipv4_ranges: List[Tuple[int, int, str]] = []
    _ipv6_ranges: List[Tuple[int, int, str]] = []
    _update_checked = False

    def __new__(cls, file_path: str = "ipset.json"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._file_path = file_path
        return cls._instance

    def __init__(self, file_path: str = "ipset.json"):
        if not IPSet._data_loaded:
            IPSet._file_path = file_path
            self.load_data()

        if not IPSet._update_checked:
            with IPSet._lock:
                if not IPSet._update_checked:
                    background_update_check(
                        IPSet._file_path,
                        IPSet._update_url,
                        on_update_callback=IPSet.reload_data,
                    )
                    IPSet._update_checked = True

    @staticmethod
    def _ip_to_int(ip_str: str) -> Tuple[int, int]:
        """Convert IP string to integer and version."""
        try:
            return struct.unpack("!I", socket.inet_aton(ip_str))[0], 4
        except socket.error as exc:
            try:
                ip_bytes = socket.inet_pton(socket.AF_INET6, ip_str)
                return int.from_bytes(ip_bytes, "big"), 6
            except socket.error:
                raise ValueError(f"Invalid IP address: {ip_str}") from exc

    @staticmethod
    def _cidr_to_range(cidr_str: str) -> Tuple[int, int, int]:
        """Convert CIDR to integer range and version."""
        network = IPNetwork(cidr_str)
        return network.first, network.last, network.version

    @staticmethod
    def _binary_search(ranges: List[Tuple[int, int, str]], ip_int: int) -> List[str]:
        """Binary search for IP in sorted ranges."""
        groups = []
        left, right = 0, len(ranges) - 1

        while left <= right:
            mid = (left + right) // 2
            start, end, group = ranges[mid]

            if ip_int < start:
                right = mid - 1
            elif ip_int > end:
                left = mid + 1
            else:
                groups.append(group)
                for i in range(mid - 1, -1, -1):
                    if ranges[i][1] >= ip_int >= ranges[i][0]:
                        groups.append(ranges[i][2])
                    else:
                        break
                for i in range(mid + 1, len(ranges)):
                    if ranges[i][0] <= ip_int <= ranges[i][1]:
                        groups.append(ranges[i][2])
                    else:
                        break
                break
        return groups

    def load_data(self):
        """Load IP data from JSON file."""
        with IPSet._lock:
            if IPSet._data_loaded:
                return

            try:
                if not os.path.exists(IPSet._file_path):
                    IPSet._data_loaded = True
                    return

                with open(IPSet._file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                ip_data = {k: v for k, v in data.items() if k != "_timestamp"}
                self._rebuild_data_structures(ip_data)
                IPSet._data_loaded = True

            except (IOError, OSError, json.JSONDecodeError):
                IPSet._data_loaded = True

    @classmethod
    def _rebuild_data_structures(cls, ip_data: Dict[str, List[str]]):
        """Rebuild the internal data structures from IP data.

        Args:
            ip_data: Dictionary mapping group names to lists of IPs/CIDRs
        """
        ip_to_groups = {}
        ipv4_ranges = []
        ipv6_ranges = []

        for group, ips in ip_data.items():
            for ip_or_cidr in ips:
                if "/" in ip_or_cidr:
                    try:
                        start, end, version = cls._cidr_to_range(ip_or_cidr)
                        if version == 4:
                            ipv4_ranges.append((start, end, group))
                        else:
                            ipv6_ranges.append((start, end, group))
                    except (ValueError, TypeError):
                        continue
                else:
                    ip_to_groups.setdefault(ip_or_cidr, []).append(group)

        ipv4_ranges.sort()
        ipv6_ranges.sort()

        cls._ip_to_groups = ip_to_groups
        cls._ipv4_ranges = ipv4_ranges
        cls._ipv6_ranges = ipv6_ranges

    @classmethod
    def reload_data(cls):
        """Reload data from file and rebuild data structures.

        This method can be called after the file has been updated
        to refresh the in-memory data structures.
        """
        with cls._lock:
            cls._data_loaded = False
            if cls._instance:
                cls._instance.load_data()

    def get_groups(self, ip: str) -> List[str]:
        """Get all groups containing the IP address."""
        groups = []

        try:
            if ip in IPSet._ip_to_groups:
                groups.extend(IPSet._ip_to_groups[ip])

            ip_int, version = self._ip_to_int(ip)
            ranges = IPSet._ipv4_ranges if version == 4 else IPSet._ipv6_ranges
            range_groups = self._binary_search(ranges, ip_int)

            for group in range_groups:
                if group not in groups:
                    groups.append(group)

        except (ValueError, socket.error):
            pass

        return groups
