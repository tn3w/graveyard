import requests
import random
import time
import concurrent.futures
import ssl
from typing import Dict
import logging
import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import threading

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import socks

    socks.create_connection
except (ImportError, AttributeError):
    logger.error(
        "Missing dependencies for SOCKS support. Please install PySocks package:"
    )
    logger.error("pip install PySocks")
    sys.exit(1)

PROXY_SSL_CONTEXT = ssl.create_default_context()
PROXY_SSL_CONTEXT.check_hostname = False
PROXY_SSL_CONTEXT.verify_mode = ssl.CERT_NONE
PROXY_SSL_CONTEXT.load_default_certs()


class ProxyCall:
    def __init__(self, target_url: str, max_workers: int = 50, timeout: int = 10):
        """
        Initialize the ProxyCall instance.

        Args:
            target_url: The URL to call
            max_workers: Maximum number of concurrent workers
            timeout: Timeout for requests in seconds
        """
        self.target_url = target_url
        self.max_workers = max_workers
        self.timeout = timeout
        self.proxies = []
        self.proxy_failures = {}
        self.proxy_response_times = {}
        self.proxy_request_count = {}
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_calls = 0
        self.start_time = time.time()

        self.user_agents_data = [
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.3",
                "pct": 40.98,
            },
            {
                "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.1",
                "pct": 12.7,
            },
            {
                "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.1",
                "pct": 12.43,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.",
                "pct": 8.74,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.",
                "pct": 6.01,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.",
                "pct": 6.01,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.",
                "pct": 2.73,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.",
                "pct": 2.19,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.",
                "pct": 2.19,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 6.1; rv:109.0) Gecko/20100101 Firefox/115.",
                "pct": 1.09,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.",
                "pct": 1.09,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.",
                "pct": 1.09,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3",
                "pct": 1.09,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 OPR/95.0.0.",
                "pct": 0.55,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.",
                "pct": 0.55,
            },
            {
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.3",
                "pct": 0.55,
            },
        ]

        self.referers = [
            "https://github.com/",
            "https://stackoverflow.com/",
            "https://dev.to/",
            "https://medium.com/",
            "https://hackernoon.com/",
            "https://www.freecodecamp.org/",
            "https://www.codecademy.com/",
            "https://www.geeksforgeeks.org/",
            "https://www.w3schools.com/",
            "https://codepen.io/",
            "https://replit.com/",
            "https://codesandbox.io/",
            "https://jsfiddle.net/",
            "https://jsbin.com/",
            "https://plnkr.co/",
            "https://glitch.com/",
            "https://stackblitz.com/",
            "https://observablehq.com/",
            "https://jupyter.org/",
            "https://runkit.com/",
            "https://scrimba.com/",
            "https://hashnode.com/",
            "https://css-tricks.com/",
            "https://scotch.io/",
            "https://sitepoint.com/",
            "https://dzone.com/",
            "https://tympanus.net/codrops/",
            "https://smashingmagazine.com/",
            "https://webdesignerdepot.com/",
            "https://codeburst.io/",
            "https://thepracticaldev.dev/",
            "https://dailydev.com/",
            "https://devdojo.com/",
            "https://devhints.io/",
            "https://frontendmasters.com/",
            "https://egghead.io/",
            "https://vueschool.io/",
            "https://laracasts.com/",
            "https://digitalocean.com/",
            "https://auth0.com/",
        ]

        self.languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9,fr-CA;q=0.8,fr;q=0.7",
            "es-ES,es;q=0.9,en;q=0.8",
            "fr-FR,fr;q=0.9,en;q=0.8",
            "de-DE,de;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.9,en;q=0.8",
            "ja-JP,ja;q=0.9,en;q=0.8",
            "ru-RU,ru;q=0.9,en;q=0.8",
            "pt-BR,pt;q=0.9,en;q=0.8",
        ]

        self.session = requests.Session()
        self.session.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                pool_connections=max_workers, pool_maxsize=max_workers, max_retries=0
            ),
        )

    def _get_weighted_user_agent(self) -> str:
        """
        Select a user agent based on the provided weights.

        Returns:
            A randomly selected user agent string weighted by popularity
        """
        total = sum(item["pct"] for item in self.user_agents_data)
        r = random.uniform(0, total)
        cumulative_weight = 0

        for item in self.user_agents_data:
            cumulative_weight += item["pct"]
            if r <= cumulative_weight:
                return item["ua"]

        return self.user_agents_data[0]["ua"]

    def _generate_browser_headers(self) -> Dict[str, str]:
        """
        Generate realistic browser headers for script resource requests.

        Returns:
            Dictionary of HTTP headers
        """
        user_agent = self._get_weighted_user_agent()

        is_chrome = "Chrome" in user_agent
        is_firefox = "Firefox" in user_agent
        is_safari = "Safari" in user_agent and "Chrome" not in user_agent
        is_edge = "Edg/" in user_agent

        headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": random.choice(self.languages),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Requested-With": "XMLHttpRequest",
            "X-Timestamp": str(time.time()),
            "Referer": random.choice(self.referers),
        }

        headers["Sec-Fetch-Dest"] = "script"
        headers["Sec-Fetch-Mode"] = "no-cors"
        headers["Sec-Fetch-Site"] = "cross-site"

        if is_chrome or is_edge:
            headers["sec-ch-ua"] = (
                '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"'
            )
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = (
                '"Windows"' if "Windows" in user_agent else '"macOS"'
            )

        return headers

    def download_proxies(self) -> None:
        """
        Download and parse proxy lists from ProxyScrape API.
        """
        logger.info("Downloading proxy lists from ProxyScrape...")

        url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=ipport&format=json"

        proxies = set()

        try:
            response = self.session.get(url, timeout=15, verify=False)
            if response.status_code == 200:
                try:
                    data = response.json()

                    if "proxies" in data:
                        proxy_list = data["proxies"]
                        logger.info(f"Found {len(proxy_list)} proxies in the response")

                        for proxy_info in proxy_list:
                            if not proxy_info.get("alive", False):
                                continue

                            protocol = proxy_info.get("protocol", "http").lower()

                            if "proxy" in proxy_info:
                                proxy_address = proxy_info["proxy"]
                                proxy_str = f"{protocol}://{proxy_address}"
                                proxies.add(proxy_str)
                            elif "ip" in proxy_info and "port" in proxy_info:
                                ip = proxy_info["ip"]
                                port = proxy_info["port"]
                                proxy_str = f"{protocol}://{ip}:{port}"
                                proxies.add(proxy_str)

                        logger.info(
                            f"Extracted {len(proxies)} working proxies from ProxyScrape"
                        )
                    else:
                        logger.warning("No 'proxies' array found in the response")
                except json.JSONDecodeError:
                    if ":" in response.text:
                        for line in response.text.strip().split("\n"):
                            line = line.strip()
                            if line and ":" in line:
                                proxies.add(f"http://{line}")
                        logger.info(
                            f"Parsed {len(proxies)} proxies from text format response"
                        )
                    else:
                        logger.warning(
                            "Could not parse response as JSON or text format"
                        )
            else:
                logger.warning(
                    f"Failed to download proxies from ProxyScrape, status code: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"Error downloading proxies from ProxyScrape: {str(e)}")

        if not proxies:
            logger.warning("No proxies found from ProxyScrape, adding fallback proxies")
            fallback_proxies = [
                "http://51.159.115.233:3128",
                "http://13.95.173.197:80",
                "http://165.227.15.186:3128",
            ]
            for proxy in fallback_proxies:
                proxies.add(proxy)

        socks_proxies = [p for p in proxies if p.startswith(("socks4://", "socks5://"))]
        if socks_proxies:
            logger.info(
                f"Found {len(socks_proxies)} SOCKS proxies out of {len(proxies)} total proxies"
            )

        self.proxies = list(proxies)

        for proxy in self.proxies:
            self.proxy_failures[proxy] = 0
            self.proxy_response_times[proxy] = None
            self.proxy_request_count[proxy] = 0

    def _select_proxy(self) -> str:
        """
        Select a proxy with preference for faster ones.

        Returns:
            A proxy URL string
        """
        if not self.proxies:
            return None


        tested_proxies = [
            p for p in self.proxies if self.proxy_response_times[p] is not None
        ]

        if len(tested_proxies) >= 5 and random.random() < 0.7:
            fastest_proxies = sorted(
                tested_proxies, key=lambda p: self.proxy_response_times[p]
            )
            num_to_use = max(
                3, len(fastest_proxies) // 3
            )

            return random.choice(fastest_proxies[:num_to_use])

        return random.choice(self.proxies)

    def _update_proxy_stats(
        self, proxy: str, elapsed_time: float, success: bool
    ) -> None:
        """
        Update statistics for a proxy.

        Args:
            proxy: The proxy URL
            elapsed_time: The time taken for the request in seconds
            success: Whether the request was successful
        """
        if success:
            if self.proxy_response_times[proxy] is None:
                self.proxy_response_times[proxy] = elapsed_time
            else:
                self.proxy_response_times[proxy] = (
                    0.8 * self.proxy_response_times[proxy] + 0.2 * elapsed_time
                )

            self.proxy_request_count[proxy] += 1
        else:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1

            if self.proxy_failures[proxy] >= 2:
                if proxy in self.proxies:
                    self.proxies.remove(proxy)
                    self._add_to_removed_proxies(proxy)
                    logger.debug(
                        f"Removed proxy {proxy} after {self.proxy_failures[proxy]} failures"
                    )

    def _add_to_removed_proxies(self, proxy: str) -> None:
        """Add a proxy to the removed proxies list with current timestamp."""
        if not hasattr(self, "removed_proxies"):
            self.removed_proxies = {}
        self.removed_proxies[proxy] = {
            "removed_at": time.time(),
            "last_check": None,
            "successful_checks": 0,
        }

    def _check_removed_proxy(self, proxy: str) -> bool:
        """
        Test a removed proxy to see if it's working again.

        Args:
            proxy: The proxy URL to test

        Returns:
            bool: True if proxy passed the test, False otherwise
        """
        test_urls = [
            "https://www.google.com/",
            "https://www.cloudflare.com/",
            "https://httpbin.org/get",
        ]

        test_url = random.choice(test_urls)
        result = self._test_proxy(proxy, test_url)

        if result["success"]:
            proxy_info = self.removed_proxies[proxy]
            proxy_info["last_check"] = time.time()
            proxy_info["successful_checks"] += 1

            if proxy_info["successful_checks"] >= 2:
                self._restore_proxy(proxy)
                return True

        return False

    def _restore_proxy(self, proxy: str) -> None:
        """
        Restore a previously removed proxy.

        Args:
            proxy: The proxy URL to restore
        """
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            self.proxy_failures[proxy] = 0
            self.proxy_response_times[proxy] = None
            self.proxy_request_count[proxy] = 0
            if proxy in self.removed_proxies:
                del self.removed_proxies[proxy]
            logger.info(f"Restored proxy {proxy} after passing recovery checks")

    def _start_proxy_recovery(self, wait_mode: bool = False) -> None:
        """
        Start a background thread for proxy recovery.

        Args:
            wait_mode: If True, uses continuous checking for rate-limited mode.
                     If False, only checks proxies after 5 minutes cooldown.
        """

        def recovery_worker():
            while True:
                if not hasattr(self, "removed_proxies") or not self.removed_proxies:
                    time.sleep(10)
                    continue

                current_time = time.time()

                for proxy in list(
                    self.removed_proxies.keys()
                ):
                    proxy_info = self.removed_proxies[proxy]

                    if wait_mode:
                        if (
                            proxy_info["last_check"] is None
                            or (current_time - proxy_info["last_check"]) > 30
                        ):
                            self._check_removed_proxy(proxy)
                    else:
                        if (current_time - proxy_info["removed_at"]) >= 300 and (
                            proxy_info["last_check"] is None
                            or (current_time - proxy_info["last_check"]) >= 300
                        ):
                            self._check_removed_proxy(proxy)

                time.sleep(5)

        recovery_thread = threading.Thread(target=recovery_worker, daemon=True)
        recovery_thread.start()
        logger.info("Started proxy recovery system")

    def _get_cache_path(self) -> Path:
        """Get the path to the proxy cache file."""
        cache_dir = Path.home() / ".proxycall"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / "proxy_cache.json"

    def _save_proxy_cache(self) -> None:
        """Save proxy test results to cache file."""
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "proxies": self.proxies,
            "response_times": self.proxy_response_times,
            "failures": self.proxy_failures,
            "request_count": self.proxy_request_count,
        }

        try:
            with open(self._get_cache_path(), "w") as f:
                json.dump(cache_data, f)
            logger.info("Proxy test results cached successfully")
        except Exception as e:
            logger.warning(f"Failed to save proxy cache: {e}")

    def _load_proxy_cache(self) -> bool:
        """
        Load proxy test results from cache if available and not expired.

        Returns:
            bool: True if valid cache was loaded, False otherwise
        """
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, "r") as f:
                cache_data = json.load(f)

            cache_time = datetime.fromisoformat(cache_data["timestamp"])
            if datetime.now() - cache_time > timedelta(hours=1):
                logger.info("Proxy cache expired, will test proxies again")
                return False

            self.proxies = cache_data["proxies"]
            self.proxy_response_times = cache_data["response_times"]
            self.proxy_failures = cache_data["failures"]
            self.proxy_request_count = cache_data["request_count"]

            logger.info(
                f"Loaded {len(self.proxies)} proxies from cache (cached at {cache_time})"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to load proxy cache: {e}")
            return False

    def _make_single_call(self, custom_url: str = None) -> Dict:
        """
        Make a single call to the target URL using a selected proxy.

        Args:
            custom_url: Optional custom URL to call instead of the target URL

        Returns:
            Dictionary with response information
        """
        if not self.proxies:
            logger.warning("No more valid proxies available")
            self.failed_calls += 1
            self.total_calls += 1
            return {
                "success": False,
                "error": "No valid proxies available",
                "proxy": None,
                "status_code": None,
            }

        proxy = self._select_proxy()
        proxy_dict = {"https": proxy, "http": proxy}

        headers = self._generate_browser_headers()

        url_to_call = custom_url if custom_url else self.target_url

        try:
            start_time = time.time()
            response = self.session.get(
                url_to_call,
                proxies=proxy_dict,
                headers=headers,
                timeout=self.timeout,
                verify=False,
            )
            elapsed_time = time.time() - start_time

            if not custom_url:
                self._update_proxy_stats(proxy, elapsed_time, True)

                self.successful_calls += 1
                self.total_calls += 1

                if self.total_calls % 100 == 0:
                    success_rate = (self.successful_calls / self.total_calls) * 100
                    tested_proxies = [
                        p
                        for p in self.proxies
                        if self.proxy_response_times[p] is not None
                    ]

                    if tested_proxies:
                        fastest_proxy = min(
                            tested_proxies, key=lambda p: self.proxy_response_times[p]
                        )
                        fastest_time = self.proxy_response_times[fastest_proxy]
                        logger.info(
                            f"Progress: {self.successful_calls} successful calls out of {self.total_calls} attempts ({success_rate:.1f}%). Fastest proxy: {fastest_time:.2f}s"
                        )
                    else:
                        logger.info(
                            f"Progress: {self.successful_calls} successful calls out of {self.total_calls} attempts ({success_rate:.1f}%)"
                        )

            return {
                "success": True,
                "status_code": response.status_code,
                "elapsed_seconds": elapsed_time,
                "proxy": proxy,
                "response_size": (
                    len(response.content) if hasattr(response, "content") else 0
                ),
                "user_agent": headers["User-Agent"],
            }

        except Exception as e:
            if not custom_url:
                self.failed_calls += 1
                self.total_calls += 1

                self._update_proxy_stats(proxy, 0, False)
            else:
                self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1

                if self.proxy_failures[proxy] >= 2:
                    if proxy in self.proxies:
                        self.proxies.remove(proxy)
                        logger.debug(
                            f"Removed proxy {proxy} after {self.proxy_failures[proxy]} failures during testing"
                        )

            return {
                "success": False,
                "error": str(e),
                "proxy": proxy,
                "status_code": None,
            }

    def _test_proxy(self, proxy: str, test_url: str) -> Dict:
        """
        Test a specific proxy with a test URL.

        Args:
            proxy: The proxy URL to test
            test_url: The URL to use for testing

        Returns:
            Dictionary with test result information
        """
        proxy_dict = {"https": proxy, "http": proxy}
        headers = self._generate_browser_headers()

        try:
            start_time = time.time()
            response = self.session.get(
                test_url,
                proxies=proxy_dict,
                headers=headers,
                timeout=self.timeout,
                verify=False,
            )
            elapsed_time = time.time() - start_time

            if self.proxy_response_times[proxy] is None:
                self.proxy_response_times[proxy] = elapsed_time
            else:
                self.proxy_response_times[proxy] = (
                    self.proxy_response_times[proxy] + elapsed_time
                ) / 2

            return {
                "success": True,
                "elapsed_seconds": elapsed_time,
                "status_code": response.status_code,
            }

        except Exception as e:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1

            if self.proxy_failures[proxy] >= 2:
                if proxy in self.proxies:
                    self.proxies.remove(proxy)

            return {"success": False, "error": str(e)}

    def test_all_proxies(self):
        """
        Test all proxies and establish a baseline for performance.
        Tests each proxy twice with reliable test URLs in parallel.
        First tries to load from cache, if not available or expired,
        performs actual testing.
        """
        if self._load_proxy_cache():
            return len(self.proxies) > 0

        logger.info(
            "Testing all proxies in parallel to establish baseline performance..."
        )

        test_urls = [
            "https://www.google.com/",
            "https://www.cloudflare.com/",
            "https://httpbin.org/get",
        ]

        original_proxy_count = len(self.proxies)

        if original_proxy_count == 0:
            logger.error("No proxies to test.")
            return False

        logger.info(f"Starting parallel testing of {original_proxy_count} proxies...")

        def test_proxy_task(proxy_and_attempt):
            proxy, attempt = proxy_and_attempt

            if proxy not in self.proxies:
                return {
                    "proxy": proxy,
                    "success": False,
                    "error": "Proxy already removed",
                    "attempt": attempt,
                }

            if attempt == 1 and self.proxy_failures.get(proxy, 0) >= 1:
                return {
                    "proxy": proxy,
                    "success": False,
                    "error": "Previous test failed",
                    "attempt": attempt,
                }

            test_url = random.choice(test_urls)

            result = self._test_proxy(proxy, test_url)
            result["proxy"] = proxy
            result["attempt"] = attempt
            return result

        tasks = []
        for proxy in list(self.proxies):
            tasks.append((proxy, 0))
            tasks.append((proxy, 1))

        test_workers = min(50, len(tasks))
        completed = 0
        successful_tests = 0

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=test_workers
        ) as executor:
            future_to_task = {
                executor.submit(test_proxy_task, task): task for task in tasks
            }

            for future in concurrent.futures.as_completed(future_to_task):
                completed += 1

                try:
                    result = future.result()
                    proxy = result["proxy"]
                    attempt = result["attempt"]

                    if result["success"]:
                        successful_tests += 1
                        elapsed = result["elapsed_seconds"]
                        logger.debug(
                            f"Test {attempt+1}/2 for {proxy} success: {elapsed:.3f}s"
                        )
                    else:
                        logger.debug(
                            f"Test {attempt+1}/2 for {proxy} failed: {result.get('error', 'Unknown error')}"
                        )

                    if completed % 20 == 0 or completed == len(tasks):
                        progress_pct = (completed / len(tasks)) * 100
                        logger.info(
                            f"Testing progress: {completed}/{len(tasks)} tests completed ({progress_pct:.1f}%)"
                        )

                except Exception as e:
                    logger.debug(f"Error in test task: {str(e)}")

        working_proxies = [
            p for p in self.proxies if self.proxy_response_times[p] is not None
        ]

        logger.info(
            f"Proxy testing complete. {len(working_proxies)}/{original_proxy_count} proxies working"
        )

        if working_proxies:
            fastest_proxies = sorted(
                working_proxies, key=lambda p: self.proxy_response_times[p]
            )[:5]

            logger.info("Top 5 fastest proxies from testing:")
            for i, proxy in enumerate(fastest_proxies, 1):
                logger.info(f"{i}. {proxy} - {self.proxy_response_times[proxy]:.3f}s")

        self._save_proxy_cache()

        return len(working_proxies) > 0

    def run_continuously(self):
        """
        Run as many parallel requests as possible until stopped.
        """
        if not self.proxies:
            logger.error("No proxies available. Exiting.")
            return

        self._start_proxy_recovery(wait_mode=False)

        logger.info(
            f"Making parallel calls to {self.target_url} with {self.max_workers} workers"
        )
        logger.info("Press Ctrl+C to stop and see results")

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

        try:
            futures = {
                executor.submit(self._make_single_call): i
                for i in range(self.max_workers)
            }

            while True:
                done, not_done = concurrent.futures.wait(
                    futures,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                    timeout=0.1,
                )

                if not done:
                    continue

                for future in done:
                    try:
                        future.result()
                    except Exception as exc:
                        logger.debug(f"Task generated an exception: {exc}")

                    del futures[future]

                    new_future = executor.submit(self._make_single_call)
                    futures[new_future] = len(futures)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            for future in futures:
                future.cancel()

            executor.shutdown(wait=False)

        finally:
            if not executor._shutdown:
                executor.shutdown(wait=False)

            self.print_summary()

    def run_sequentially(self, wait_ms: int):
        """
        Run requests sequentially with a specified wait time between requests.
        First tests all proxies to establish a baseline, then makes actual requests.

        Args:
            wait_ms: The time to wait between requests in milliseconds
        """
        if not self.proxies:
            logger.error("No proxies available. Exiting.")
            return

        self._start_proxy_recovery(wait_mode=True)

        logger.info("Starting proxy testing phase...")
        if not self.test_all_proxies():
            logger.error("No working proxies found after testing. Exiting.")
            return

        logger.info(
            f"Making sequential calls to {self.target_url} with {wait_ms}ms delay between requests"
        )
        logger.info("Press Ctrl+C to stop and see results")

        try:
            while True:
                proxy = self._select_proxy()

                if not proxy:
                    logger.error("No valid proxies available. Exiting.")
                    break

                result = self._make_single_call()

                if result["success"]:
                    logger.info(
                        f"Request {self.total_calls}: Success ({result['status_code']}) - {result['proxy']} - {result['elapsed_seconds']:.3f}s"
                    )
                else:
                    logger.info(
                        f"Request {self.total_calls}: Failed - {result['proxy']} - {result.get('error', 'Unknown error')}"
                    )

                time.sleep(wait_ms / 1000)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping...")
        finally:
            self.print_summary()

    def run_rate_limited(self, rate_ms: int):
        """
        Run requests in parallel but with a rate limit.
        First tests all proxies to establish a baseline, then makes parallel
        requests at the specified rate. Dynamically adjusts the rate based on
        actual performance.

        Args:
            rate_ms: The target time between requests in milliseconds
                     (used to calculate requests per minute)
        """
        if not self.proxies:
            logger.error("No proxies available. Exiting.")
            return

        self._start_proxy_recovery(wait_mode=True)

        logger.info("Starting proxy testing phase...")
        if not self.test_all_proxies():
            logger.error("No working proxies found after testing. Exiting.")
            return

        requests_per_minute = int(60 * (1000 / rate_ms))
        requests_per_second = requests_per_minute / 60

        logger.info(f"Running in rate-limited parallel mode")
        logger.info(
            f"Initial target rate: {requests_per_minute} requests per minute ({requests_per_second:.2f}/second)"
        )
        logger.info(f"Making parallel calls to {self.target_url}")
        logger.info("Press Ctrl+C to stop and see results")

        effective_workers = min(self.max_workers, requests_per_minute)

        last_request_time = time.time()
        min_delay = rate_ms / 1000
        last_rate_adjustment = time.time()
        rate_adjustment_interval = 10
        
        wait_time_history = []
        max_history = 5
        last_adjustment_direction = None
        consecutive_increases = 0

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers)
        futures = {}
        start_time = time.time()

        try:
            initial_batch = min(
                effective_workers, int(requests_per_second * 3)
            )
            logger.info(f"Starting with {initial_batch} initial requests")

            for i in range(initial_batch):
                future = executor.submit(self._make_single_call)
                futures[future] = time.time()
                time.sleep(0.05)

            while True:
                current_time = time.time()

                if (
                    current_time - last_rate_adjustment >= rate_adjustment_interval
                    and self.total_calls > 50
                ):
                    elapsed_time = current_time - start_time
                    actual_wait_ms = (elapsed_time / self.total_calls) * 1000
                    actual_rate = (self.total_calls / elapsed_time) * 60

                    wait_time_history.append(actual_wait_ms)
                    if len(wait_time_history) > max_history:
                        wait_time_history.pop(0)

                    wait_time_increasing = len(wait_time_history) >= 2 and all(
                        wait_time_history[i] < wait_time_history[i + 1]
                        for i in range(len(wait_time_history) - 1)
                    )

                    target_rpm = int(60 * (1000 / rate_ms))
                    
                    if abs(actual_wait_ms - rate_ms) / rate_ms > 0.05:
                        if actual_wait_ms > rate_ms:
                            if wait_time_increasing and consecutive_increases >= 2:
                                requests_per_minute = int(requests_per_minute * 0.85)
                                consecutive_increases = 0
                                last_adjustment_direction = "decrease"
                                logger.info(
                                    f"Wait times consistently increasing ({actual_wait_ms:.1f}ms), backing off to {requests_per_minute} req/min"
                                )
                            else:
                                slowdown_ratio = actual_wait_ms / rate_ms
                                increase_factor = 1.1 + min(0.2, (slowdown_ratio - 1) * 0.2)
                                requests_per_minute = int(target_rpm * increase_factor)
                                
                                if last_adjustment_direction == "increase":
                                    consecutive_increases += 1
                                else:
                                    consecutive_increases = 1
                                last_adjustment_direction = "increase"
                                
                                logger.info(
                                    f"Actual wait ({actual_wait_ms:.1f}ms) higher than target ({rate_ms}ms), "
                                    f"increasing target rate to {requests_per_minute} req/min (adjustment factor: {increase_factor:.2f}x)"
                                )
                        else:
                            decrease_factor = 0.9
                            requests_per_minute = int(target_rpm * decrease_factor)
                            consecutive_increases = 0
                            last_adjustment_direction = "decrease"
                            logger.info(
                                f"Actual wait ({actual_wait_ms:.1f}ms) lower than target ({rate_ms}ms), "
                                f"decreasing target rate to {requests_per_minute} req/min"
                            )

                        requests_per_second = requests_per_minute / 60
                        min_delay = (1000 / (requests_per_minute / 60)) / 1000

                        new_workers = min(self.max_workers, requests_per_minute)
                        if new_workers != effective_workers:
                            effective_workers = new_workers
                            executor._max_workers = effective_workers

                    last_rate_adjustment = current_time

                done, not_done = concurrent.futures.wait(
                    list(futures.keys()),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                    timeout=0.1,
                )

                if not done:
                    continue

                for future in done:
                    try:
                        future.result()
                    except Exception as exc:
                        logger.debug(f"Task generated an exception: {exc}")

                    del futures[future]

                elapsed = current_time - last_request_time
                time_since_start = current_time - start_time

                expected_requests = int(time_since_start * requests_per_second)
                actual_requests = self.total_calls + len(futures)
                requests_to_add = max(0, min(3, expected_requests - actual_requests))

                if requests_to_add > 0 and elapsed >= min_delay:
                    for i in range(requests_to_add):
                        new_future = executor.submit(self._make_single_call)
                        futures[new_future] = current_time

                    last_request_time = current_time

                    if self.total_calls % 50 == 0 and self.total_calls > 0:
                        actual_rate = self.total_calls / time_since_start * 60
                        logger.info(
                            f"Current rate: {actual_rate:.1f} requests/minute (target: {requests_per_minute}), Active requests: {len(futures)}"
                        )

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            for future in list(futures.keys()):
                future.cancel()

            executor.shutdown(wait=False)

        finally:
            if not executor._shutdown:
                executor.shutdown(wait=False)

            self.print_summary()

    def print_summary(self):
        """Print a summary of results."""
        logger.info("=" * 50)
        logger.info("RESULTS SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total requests made: {self.total_calls}")
        logger.info(f"Successful requests: {self.successful_calls}")
        logger.info(f"Failed requests: {self.failed_calls}")

        if self.total_calls > 0:
            success_rate = (self.successful_calls / self.total_calls) * 100
            logger.info(f"Success rate: {success_rate:.2f}%")

            elapsed_time = time.time() - self.start_time
            actual_rate_per_minute = (self.total_calls / elapsed_time) * 60
            actual_wait_ms = (
                (elapsed_time / self.total_calls) * 1000 if self.total_calls > 1 else 0
            )

            logger.info(f"Actual rate: {actual_rate_per_minute:.2f} requests/minute")
            logger.info(f"Average wait between requests: {actual_wait_ms:.2f}ms")

        logger.info(f"Remaining working proxies: {len(self.proxies)}")

        if hasattr(self, "removed_proxies") and self.removed_proxies:
            logger.info(f"\nProxies in recovery: {len(self.removed_proxies)}")
            recovering_proxies = []
            for proxy, info in self.removed_proxies.items():
                time_since_removal = time.time() - info["removed_at"]
                successful_checks = info["successful_checks"]
                recovering_proxies.append(
                    (proxy, time_since_removal, successful_checks)
                )

            recovering_proxies.sort(key=lambda x: (-x[2], x[1]))

            logger.info("\nTop 5 proxies in recovery:")
            for i, (proxy, time_since_removal, checks) in enumerate(
                recovering_proxies[:5], 1
            ):
                minutes = time_since_removal / 60
                logger.info(
                    f"{i}. {proxy} - {minutes:.1f}m ago, {checks}/2 successful checks"
                )

        tested_proxies = [
            p for p in self.proxies if self.proxy_response_times[p] is not None
        ]
        if tested_proxies:
            fastest_proxies = sorted(
                tested_proxies, key=lambda p: self.proxy_response_times[p]
            )[:5]

            logger.info("\nTop 5 fastest proxies:")
            for i, proxy in enumerate(fastest_proxies, 1):
                response_time = self.proxy_response_times[proxy]
                requests_made = self.proxy_request_count[proxy]
                logger.info(
                    f"{i}. {proxy} - {response_time:.3f}s (used {requests_made} times)"
                )

        logger.info("=" * 50)


def main():
    """Run the script with command-line arguments."""
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )

    parser = argparse.ArgumentParser(description="Make requests through multiple proxies")
    parser.add_argument("url", help="Target URL to send requests to")
    parser.add_argument("--wait", type=int, default=0, 
                        help="Wait time between requests in milliseconds (for rate-limited mode)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Timeout for requests in seconds")
    parser.add_argument("--workers", type=int, 
                        default=min(os.cpu_count() * 5, 200),
                        help="Maximum number of concurrent workers")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose debug logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    target_url = args.url
    wait_ms = args.wait
    max_workers = args.workers
    timeout = args.timeout
    
    rate_limited_mode = False
    sequential_mode = False
    
    if wait_ms > 0:
        rate_limited_mode = True
        logger.info(
            f"Running in rate-limited parallel mode with {wait_ms}ms target rate"
        )
    elif wait_ms < 0:
        sequential_mode = True
        wait_ms = abs(wait_ms)
        logger.info(
            f"Running in sequential mode with {wait_ms}ms delay between requests"
        )

    proxy_call = ProxyCall(target_url=target_url, max_workers=max_workers, timeout=timeout)

    proxy_call.download_proxies()

    if not proxy_call.proxies:
        logger.error("No valid proxies found. Exiting.")
        return

    if rate_limited_mode:
        proxy_call.run_rate_limited(wait_ms)
    elif sequential_mode:
        proxy_call.run_sequentially(wait_ms)
    else:
        proxy_call.run_continuously()


if __name__ == "__main__":
    main()
