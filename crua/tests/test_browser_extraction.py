#!/usr/bin/env python3

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from crua import parse


class TestBrowserDetection:
    @pytest.mark.parametrize(
        ("ua", "expected_browser", "expected_version"),
        [
            (
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0.0.0 Safari/537.36 Edg/110.0",
                "Edge",
                "110.0",
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0.0.0 Safari/537.36 OPR/96.0",
                "Opera",
                "96.0",
            ),
            (
                "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 SamsungBrowser/21.0 Chrome/110.0 Mobile Safari/537.36",
                "Samsung Browser",
                "21.0",
            ),
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 FxiOS/109.0 Mobile/15E148 Safari/604.1",
                "Firefox iOS",
                "109.0",
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0.0.0 Safari/537.36",
                "Chrome",
                "110.0.0.0",
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/109.0",
                "Firefox",
                "109.0",
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 Version/16.3 Safari/605.1.15",
                "Safari",
                "16.3",
            ),
        ],
    )
    def test_browser_and_version(self, ua, expected_browser, expected_version):
        result = parse(ua)
        assert result.browser is not None
        assert result.browser.browser == expected_browser
        assert result.browser.browser_version == expected_version

    def test_none_when_no_match(self):
        result = parse("Lynx/2.8.9 libwww-FM/2.14")
        assert result.browser is not None
        assert result.browser.browser is None


class TestEngineDetection:
    def test_webkit(self):
        result = parse(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
        )
        assert result.browser is not None
        assert result.browser.engine == "AppleWebKit"
        assert result.browser.engine_version == "605.1.15"

    def test_trident(self):
        result = parse(
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)"
        )
        assert result.browser is not None
        assert result.browser.engine == "Trident"
        assert result.browser.engine_version == "6.0"

    def test_gecko(self):
        result = parse(
            "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/109.0"
        )
        assert result.browser is not None
        assert result.browser.engine == "Gecko"

    def test_none(self):
        result = parse("Lynx/2.8.9 libwww-FM/2.14")
        assert result.browser is not None
        assert result.browser.engine is None


class TestOsDetection:
    @pytest.mark.parametrize(
        ("ua", "expected_os", "expected_version"),
        [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
                "Windows",
                "10/11",
            ),
            (
                "Mozilla/5.0 (compatible; MSIE 9.0; Windows Mobile; Trident/5.0)",
                "Windows Mobile",
                None,
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
                "macOS",
                "10.15.7",
            ),
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 Version/16.3 Mobile/15E148 Safari/604.1",
                "iOS",
                "16.3",
            ),
            (
                "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/110.0 Mobile Safari/537.36",
                "Android",
                "13",
            ),
            (
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0",
                "Ubuntu",
                None,
            ),
            (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
                "Linux",
                None,
            ),
        ],
    )
    def test_os_and_version(self, ua, expected_os, expected_version):
        result = parse(ua)
        assert result.browser is not None
        assert result.browser.os == expected_os
        assert result.browser.os_version == expected_version

    def test_macos_no_version(self):
        result = parse("Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36")
        assert result.browser is not None
        assert result.browser.os == "macOS"
        assert result.browser.os_version is None

    def test_ios_no_version(self):
        result = parse(
            "Mozilla/5.0 (iPhone; CPU iPhone OS like Mac OS X) AppleWebKit/605.1.15"
        )
        assert result.browser is not None
        assert result.browser.os == "iOS"
        assert result.browser.os_version is None

    def test_ios_cpu_os_without_ipad(self):
        result = parse(
            "Mozilla/5.0 (iPod; CPU OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 Version/16.0 Mobile/15E148 Safari/604.1"
        )
        assert result.browser is not None
        assert result.browser.os == "iOS"
        assert result.browser.os_version == "16.0"

    def test_ipados_with_version(self):
        result = parse(
            "Mozilla/5.0 (iPad; CPU OS 16_3 like Mac OS X) "
            "AppleWebKit/605.1.15 Version/16.3 Mobile/15E148 Safari/604.1"
        )
        assert result.browser is not None
        assert result.browser.os == "iPadOS"
        assert result.browser.os_version == "16.3"

    def test_ipados_no_version(self):
        result = parse("Mozilla/5.0 (iPad; CPU OS like Mac OS X) AppleWebKit/605.1.15")
        assert result.browser is not None
        assert result.browser.os == "iPadOS"
        assert result.browser.os_version is None

    def test_ipad_crios_without_version_reports_ios(self):
        result = parse(
            "Mozilla/5.0 (iPad; CPU OS like Mac OS X) AppleWebKit/605.1.15 CriOS/114.0"
        )
        assert result.browser is not None
        assert result.browser.os == "iOS"
        assert result.browser.os_version is None

    def test_ipad_without_cpu_os(self):
        result = parse("Mozilla/5.0 (iPad; U; en-us) AppleWebKit/537.36")
        assert result.browser is not None
        assert result.browser.os == "iPadOS"
        assert result.browser.os_version is None

    def test_none(self):
        result = parse("Lynx/2.8.9 libwww-FM/2.14")
        assert result.browser is not None
        assert result.browser.os is None


class TestDeviceDetection:
    @pytest.mark.parametrize(
        ("ua", "expected_device"),
        [
            (
                "Mozilla/5.0 (iPad; CPU OS 16_3 like Mac OS X) AppleWebKit/605.1.15 Version/16.3 Mobile/15E148 Safari/604.1",
                "Tablet",
            ),
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 Version/16.3 Mobile/15E148 Safari/604.1",
                "Mobile",
            ),
            (
                "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/110.0 Mobile Safari/537.36",
                "Mobile",
            ),
            (
                "Mozilla/5.0 (Linux; Android 13; SM-T870) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
                "Tablet",
            ),
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
                "Desktop",
            ),
        ],
    )
    def test_device(self, ua, expected_device):
        result = parse(ua)
        assert result.browser is not None
        assert result.browser.device == expected_device

    def test_tizen_tv_device(self):
        result = parse(
            "Mozilla/5.0 (Linux; Tizen 6.0; TV) AppleWebKit/537.36 Version/6.0 Safari/537.36"
        )
        assert result.browser is not None
        assert result.browser.device == "SmartTV"


class TestBrowserInfoFields:
    def test_product_token(self):
        result = parse(
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0 Safari/537.36"
        )
        assert result.browser is not None
        assert result.browser.product_token == "Mozilla/5.0"

    def test_comment_extracted(self):
        result = parse(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/110.0 Safari/537.36"
        )
        assert result.browser is not None
        assert result.browser.comment == "(Windows NT 10.0; Win64; x64)"

    def test_rendering_khtml_like_gecko(self):
        result = parse(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0 Safari/537.36"
        )
        assert result.browser is not None
        assert result.browser.rendering == "KHTML, like Gecko"

    def test_rendering_khtml_only(self):
        result = parse("Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.10")
        assert result.browser is not None
        assert result.browser.rendering == "KHTML"

    def test_rendering_none(self):
        result = parse(
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0 Safari/537.36"
        )
        assert result.browser is not None
        assert result.browser.rendering is None

    def test_browser_false_skips_info(self):
        result = parse(
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
            browser=False,
        )
        assert result.browser is None


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
BROWSER_PARSE_FILE = FIXTURES_DIR / "browser_parse.csv"


def load_browser_fixtures() -> list[dict]:
    with BROWSER_PARSE_FILE.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


_BROWSER_FIXTURES = load_browser_fixtures()


class TestBrowserParseFixtures:
    def test_fixture_count(self):
        assert len(_BROWSER_FIXTURES) >= 14000

    @pytest.mark.parametrize("row", _BROWSER_FIXTURES, ids=lambda r: r["ua"])
    def test_browser(self, row):
        result = parse(row["ua"])
        assert result.browser is not None
        assert (result.browser.browser or "") == row["browser"]

    @pytest.mark.parametrize("row", _BROWSER_FIXTURES, ids=lambda r: r["ua"])
    def test_browser_version(self, row):
        result = parse(row["ua"])
        assert result.browser is not None
        assert (result.browser.browser_version or "") == row["browser_version"]

    @pytest.mark.parametrize("row", _BROWSER_FIXTURES, ids=lambda r: r["ua"])
    def test_engine(self, row):
        result = parse(row["ua"])
        assert result.browser is not None
        assert (result.browser.engine or "") == row["engine"]

    @pytest.mark.parametrize("row", _BROWSER_FIXTURES, ids=lambda r: r["ua"])
    def test_os(self, row):
        result = parse(row["ua"])
        assert result.browser is not None
        assert (result.browser.os or "") == row["os"]

    @pytest.mark.parametrize("row", _BROWSER_FIXTURES, ids=lambda r: r["ua"])
    def test_device(self, row):
        result = parse(row["ua"])
        assert result.browser is not None
        assert (result.browser.device or "") == row["device"]


if __name__ == "__main__":
    import pytest as _pytest

    raise SystemExit(_pytest.main([str(Path(__file__).resolve())]))
