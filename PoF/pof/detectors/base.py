"""Base classes for the detection system."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, TypeVar
from flask import g, request

T = TypeVar("T", bound="BaseResult")


@dataclass
class BaseResult:
    """Base class for all detection results."""

    timestamp: float | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    @property
    def is_bot(self) -> bool:
        """Check if the result indicates bot behavior."""
        return False


class BaseDetector(ABC):
    """Base class for all detectors."""

    def __init__(self, enabled: bool = True, cache_ttl: int = 3600):
        """Initialize the detector.

        Args:
            enabled: Whether this detector is enabled
            cache_ttl: Cache time-to-live in seconds
        """
        self.enabled = enabled
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, BaseResult] = {}

    @abstractmethod
    def detect(self, **kwargs) -> BaseResult:
        """Perform detection and return result.

        Args:
            **kwargs: Detection parameters

        Returns:
            Detection result
        """

    @abstractmethod
    def get_cache_key(self, **kwargs) -> str:
        """Generate cache key for the given parameters.

        Args:
            **kwargs: Detection parameters

        Returns:
            Cache key string
        """

    def get_cached_result(self, cache_key: str) -> Optional[BaseResult]:
        """Get cached result if valid.

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None if not found/expired
        """
        if cache_key in self._cache:
            result = self._cache[cache_key]
            if (
                result.timestamp is not None
                and time.time() - result.timestamp < self.cache_ttl
            ):
                return result
            del self._cache[cache_key]
        return None

    def cache_result(self, cache_key: str, result: BaseResult) -> None:
        """Cache a detection result.

        Args:
            cache_key: Cache key
            result: Result to cache
        """
        self._cache[cache_key] = result

    def detect_with_cache(self, **kwargs) -> BaseResult:
        """Perform detection with caching.

        Args:
            **kwargs: Detection parameters

        Returns:
            Detection result (cached or fresh)
        """
        if not self.enabled:
            return BaseResult()

        cache_key = self.get_cache_key(**kwargs)

        cached_result = self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        result = self.detect(**kwargs)

        self.cache_result(cache_key, result)

        return result


class DetectionManager:
    """Manages multiple detectors and combines their results."""

    def __init__(self, detectors: Optional[List[BaseDetector]] = None):
        """Initialize the detection manager.

        Args:
            detectors: List of detectors to use
        """
        self.detectors = detectors or []

    def add_detector(self, detector: BaseDetector) -> None:
        """Add a detector to the manager.

        Args:
            detector: Detector to add
        """
        self.detectors.append(detector)

    def detect_for_request(self) -> Dict[str, BaseResult]:
        """Perform detection for the current Flask request.

        Returns:
            Dictionary mapping detector class names to results
        """
        results = {}

        ip = request.remote_addr or "127.0.0.1"
        user_agent = request.headers.get("User-Agent", "")

        for detector in self.detectors:
            if not detector.enabled:
                continue

            detector_name = detector.__class__.__name__

            try:
                if hasattr(detector, "detect_ip") and hasattr(
                    detector, "detect_user_agent"
                ):
                    result = detector.detect_with_cache(ip=ip, user_agent=user_agent)
                elif "UserAgent" in detector_name:
                    result = detector.detect_with_cache(user_agent=user_agent)
                elif "IP" in detector_name or "Api" in detector_name:
                    result = detector.detect_with_cache(ip=ip)
                else:
                    result = detector.detect_with_cache(ip=ip, user_agent=user_agent)

                results[detector_name] = result

            except Exception as e:
                print(f"Error in detector {detector_name}: {e}")
                results[detector_name] = BaseResult()

        return results

    def is_bot(self) -> bool:
        """Check if the current request is from a bot.

        Returns:
            True if any detector indicates bot behavior
        """
        results = self.detect_for_request()
        return any(result.is_bot for result in results.values())

    def get_client_cache_key(self) -> str:
        """Generate a cache key for the current client.

        Returns:
            Cache key based on IP and User-Agent
        """
        ip = request.remote_addr or "127.0.0.1"
        user_agent = request.headers.get("User-Agent", "")
        return f"{ip}:{hash(user_agent)}"

    def get_cached_client_results(self) -> Optional[Dict[str, BaseResult]]:
        """Get cached results for the current client.

        Returns:
            Cached results or None if not found
        """
        cache_key = f"client_detection:{self.get_client_cache_key()}"

        if hasattr(g, "detection_cache") and cache_key in g.detection_cache:
            cached_data = g.detection_cache[cache_key]
            if time.time() - cached_data["timestamp"] < 300:
                return cached_data["results"]

        return None

    def cache_client_results(self, results: Dict[str, BaseResult]) -> None:
        """Cache results for the current client.

        Args:
            results: Results to cache
        """
        cache_key = f"client_detection:{self.get_client_cache_key()}"

        if not hasattr(g, "detection_cache"):
            g.detection_cache = {}

        g.detection_cache[cache_key] = {"results": results, "timestamp": time.time()}

    def detect_for_client(self) -> Dict[str, BaseResult]:
        """Perform detection for the current client with caching.

        Returns:
            Dictionary mapping detector class names to results
        """
        cached_results = self.get_cached_client_results()
        if cached_results is not None:
            return cached_results

        results = self.detect_for_request()
        self.cache_client_results(results)

        return results
