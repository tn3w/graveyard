"""Base class for API-based detectors."""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .base import BaseDetector, BaseResult


class BaseApiDetector(BaseDetector, ABC):
    """Base class for API-based detectors."""

    def __init__(
        self,
        enabled: bool = True,
        cache_ttl: int = 3600,
        api_key: Optional[str] = None,
        timeout: float = 0.6,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
    ):
        """Initialize the API detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
            api_key: API key for the service (if required)
            timeout: Request timeout in seconds (max 0.6s as requested)
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Backoff factor for retries
        """
        super().__init__(enabled, cache_ttl)
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._last_request_time = 0
        self._min_request_interval = 0.1

    @abstractmethod
    def build_request_url(self, **kwargs) -> str:
        """Build the API request URL.

        Args:
            **kwargs: Parameters for the request

        Returns:
            Complete API URL
        """

    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any], **kwargs) -> BaseResult:
        """Parse the API response into a result object.

        Args:
            response_data: JSON response from the API
            **kwargs: Original request parameters

        Returns:
            Parsed result object
        """

    @abstractmethod
    def validate_parameters(self, **kwargs) -> bool:
        """Validate the parameters for the API request.

        Args:
            **kwargs: Parameters to validate

        Returns:
            True if parameters are valid
        """

    def make_request(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make an API request with rate limiting and error handling using urllib.

        Args:
            url: API URL to request
            **kwargs: Additional request parameters

        Returns:
            JSON response data or None if failed
        """
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)

        for attempt in range(self.max_retries + 1):
            try:
                headers = kwargs.get("headers", {})
                if self.api_key:
                    headers.update(self.get_auth_headers())

                params = kwargs.get("params", {})
                if params:
                    query_string = urllib.parse.urlencode(params)
                    separator = "&" if "?" in url else "?"
                    url = f"{url}{separator}{query_string}"

                req = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    self._last_request_time = time.time()

                    if response.status == 200:
                        data = response.read().decode("utf-8")
                        return json.loads(data)
                    if response.status == 429:
                        if attempt < self.max_retries:
                            wait_time = self.backoff_factor * (2**attempt)
                            time.sleep(wait_time)
                            continue
                        return None

                    print(f"API request failed with status {response.status}")
                    return None

            except urllib.error.HTTPError as e:
                print(f"HTTP error: {e.code} - {e.reason}")
                return None
            except urllib.error.URLError as e:
                print(f"URL error: {e.reason}")
                return None
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return None
            except Exception as e:
                print(f"API request error: {e}")
                return None

        return None

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the API.

        Returns:
            Dictionary of headers
        """
        return {}

    def detect(self, **kwargs) -> BaseResult:
        """Perform detection using the API.

        Args:
            **kwargs: Detection parameters

        Returns:
            Detection result
        """
        if not self.validate_parameters(**kwargs):
            return BaseResult()

        url = self.build_request_url(**kwargs)

        response_data = self.make_request(url, **kwargs)

        if response_data is None:
            return BaseResult()

        return self.parse_response(response_data, **kwargs)
