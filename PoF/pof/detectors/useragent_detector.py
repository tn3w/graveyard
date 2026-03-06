"""User Agent based bot detection."""

import re
from dataclasses import dataclass
from typing import Optional

try:
    from crawleruseragents import (
        CRAWLER_USER_AGENTS_DATA,
        is_crawler,
        matching_crawlers,
    )

    CRAWLERUSERAGENTS_AVAILABLE = True
except ImportError:
    CRAWLER_USER_AGENTS_DATA = {}

    def is_crawler(user_agent: str) -> bool:
        """Return False."""
        return user_agent in CRAWLER_USER_AGENTS_DATA

    def matching_crawlers(user_agent: str) -> list[int]:
        """Return an empty list."""
        return [0] if user_agent in CRAWLER_USER_AGENTS_DATA else []

    CRAWLERUSERAGENTS_AVAILABLE = False

from .base import BaseDetector, BaseResult


@dataclass
class UserAgentResult(BaseResult):
    """Result of User Agent detection."""

    user_agent: str = ""
    is_crawler: bool = False
    is_suspicious: bool = False
    crawler_name: Optional[str] = None
    crawler_url: Optional[str] = None

    @property
    def is_bot(self) -> bool:
        """Check if the user agent indicates bot behavior."""
        return self.is_crawler or self.is_suspicious


class UserAgentDetector(BaseDetector):
    """Detects bots based on User-Agent strings."""

    def __init__(
        self,
        enabled: bool = True,
        cache_ttl: int = 3600,
        use_matching_crawlers: bool = False,
    ):
        """Initialize the User Agent detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
            use_matching_crawlers: Whether to use matching_crawlers (slower but more detailed)
        """
        super().__init__(enabled, cache_ttl)
        self.use_matching_crawlers = (
            use_matching_crawlers and CRAWLERUSERAGENTS_AVAILABLE
        )

    def get_cache_key(self, **kwargs) -> str:
        """Generate cache key for the given parameters."""
        user_agent = kwargs.get("user_agent", "")
        return f"ua:{hash(user_agent)}"

    def detect(self, **kwargs) -> UserAgentResult:
        """Detect bot behavior based on User-Agent.

        Args:
            user_agent: User-Agent string to analyze

        Returns:
            UserAgentResult with detection results
        """
        user_agent = kwargs.get("user_agent", "")

        result = UserAgentResult(user_agent=user_agent)

        if not user_agent:
            result.is_suspicious = True
            return result

        if CRAWLERUSERAGENTS_AVAILABLE:
            if self.use_matching_crawlers:
                crawlers = matching_crawlers(user_agent)
                result.is_crawler = len(crawlers) > 0
                if result.is_crawler:
                    indices = crawlers[0]
                    result.crawler_name = CRAWLER_USER_AGENTS_DATA[indices].get(
                        "pattern", ""
                    )
                    result.crawler_url = CRAWLER_USER_AGENTS_DATA[indices].get(
                        "url", ""
                    )
            else:
                result.is_crawler = is_crawler(user_agent)
                if result.is_crawler:
                    result.crawler_name = self.get_crawler_name(user_agent)
                    result.crawler_url = self.get_crawler_url(user_agent)

        result.is_suspicious = self.is_suspicious_user_agent(user_agent)

        return result

    def get_crawler_name(self, user_agent: str) -> Optional[str]:
        """Extract crawler name from user agent string using regex.

        Assumes the input is already confirmed to be a crawler user agent.

        Args:
            user_agent: The crawler user agent string

        Returns:
            The crawler name or None if not found
        """
        if not user_agent:
            return None

        pattern = (
            r"(?:^|compatible; )"
            r"([A-Za-z][A-Za-z0-9._-]*(?:bot|spider|crawler|Bot|Spider|Crawler))"
            r"[/\s]?[\d.]*"
            r"|"
            r"^([A-Za-z][A-Za-z0-9._-]+)"
            r"(?:/[\d.]+)?"
        )

        match = re.search(pattern, user_agent)
        return match.group(1) or match.group(2) if match else None

    def get_crawler_url(self, user_agent: str) -> Optional[str]:
        """Extract crawler URL from user agent string.

        Args:
            user_agent: The user agent string

        Returns:
            The crawler URL or None if not found
        """
        if not user_agent:
            return None

        url_patterns = [
            r"\+?(https?://[^\s\)]+)",
            r"\((.*?https?://[^\s\)]+.*?)\)",
            r"https?://[^\s\)]+",
        ]

        for pattern in url_patterns:
            match = re.search(pattern, user_agent, re.IGNORECASE)
            if match:
                url = match.group(1) if match.groups() else match.group(0)
                url = re.sub(r"[^\w\-\./:?&=].*$", "", url)
                if url.startswith("http"):
                    return url

        return None

    def is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent lacks information that normal users would have.

        Args:
            user_agent: User agent string to check

        Returns:
            True if the user agent appears suspicious
        """
        if not user_agent or user_agent.strip() == "":
            return True

        if len(user_agent) < 10:
            return True

        suspicious_patterns = [
            r"^Mozilla$",
            r"^curl",
            r"^wget",
            r"^python",
            r"^java",
            r"^Go-http-client",
            r"^libwww-perl",
            r"^PHP/",
            r"^Ruby",
            r"^Node\.js",
            r"^\w+$",
        ]

        for pattern in suspicious_patterns:
            if re.match(pattern, user_agent, re.IGNORECASE):
                return True

        has_browser_info = any(
            keyword in user_agent.lower()
            for keyword in [
                "mozilla",
                "webkit",
                "gecko",
                "chrome",
                "safari",
                "firefox",
                "edge",
                "opera",
            ]
        )

        has_os_info = any(
            keyword in user_agent.lower()
            for keyword in ["windows", "mac", "linux", "android", "ios", "x11"]
        )

        if not has_browser_info and not has_os_info:
            return True

        version_patterns = [
            r"(\d+)\.(\d+)\.(\d+)\.(\d+)",
            r"(\d{4,})",
        ]

        for pattern in version_patterns:
            matches = re.findall(pattern, user_agent)
            for match in matches:
                if isinstance(match, tuple):
                    if any(int(num) > 200 for num in match if num.isdigit()):
                        return True
                elif match.isdigit() and int(match) > 1000:
                    return True

        return False
