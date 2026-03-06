"""Detection system for bot and fraud detection.

This module provides a pluggable detection system with various detection methods
including IP-based, User-Agent-based, and API-based detections.
"""

from .base import BaseDetector, BaseResult, DetectionManager
from .ipset_detector import IPSetDetector, IPSetResult
from .useragent_detector import UserAgentDetector, UserAgentResult
from .ipapi_detector import IPApiResult, IPApiComDetector, IPInfoDetector

try:
    from .ip2location_detector import IP2LocationDetector, IP2LocationResult

    IP2LOCATION_AVAILABLE = True
except ImportError:
    IP2LOCATION_AVAILABLE = False

__all__ = [
    "BaseDetector",
    "BaseResult",
    "DetectionManager",
    "IPSetDetector",
    "IPSetResult",
    "UserAgentDetector",
    "UserAgentResult",
    "IPApiResult",
    "IPApiComDetector",
    "IPInfoDetector",
]

if IP2LOCATION_AVAILABLE:
    __all__.extend(["IP2LocationDetector", "IP2LocationResult"])
