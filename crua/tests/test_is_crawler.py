#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from crua import is_crawler

TESTS_DIR = Path(__file__).resolve().parent
BROWSER_UA_FILE = TESTS_DIR / "fixtures" / "browser_user_agents.txt"
CRAWLER_UA_FILE = TESTS_DIR / "fixtures" / "crawler_user_agents.txt"


def load_user_agents(path: Path) -> list[str]:
    return [line.rstrip("\n") for line in path.read_text().splitlines() if line.strip()]


class TestCommonInputs:
    @pytest.mark.parametrize(
        ("user_agent", "expected"),
        [
            ("Googlebot/2.1 (+http://www.google.com/bot.html)", True),
            ("curl/8.7.1", True),
            ("", True),
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                False,
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36 Chrome Generic",
                False,
            ),
        ],
    )
    def test_expected_result(self, user_agent, expected):
        result = is_crawler(user_agent)
        assert isinstance(result, bool)
        assert result is expected


class TestRegressions:
    @pytest.mark.parametrize(
        ("user_agent", "expected"),
        [
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/40.0.2214.111 Safari/537.36 moatbot",
                True,
            ),
            (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/49.0.2623.75 Safari/537.36 Google Favicon",
                True,
            ),
            (
                "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0) "
                "SiteCheck-sitecrawl by Siteimprove.com",
                True,
            ),
            (
                "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0); 360Spider",
                True,
            ),
            (
                "Mozilla/5.0 (compatible; Konqueror/3.5; Linux) "
                "KHTML/3.5.5 (like Gecko) (Exabot-Thumbnails)",
                False,
            ),
            (
                "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; User-agent: "
                "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1); "
                ".NET CLR 2.0.50727; .NET CLR 1.1.4322) Sleipnir/2.8.4",
                False,
            ),
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 12_0_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/16A404 "
                "[FBAN/FBIOS;FBAV/196.0.0.52.95;FBBV/129677436;FBDV/iPhone10,4;"
                "FBMD/iPhone;FBSN/iOS;FBSV/12.0.1;FBSS/2;FBCR/Carrier;FBID/phone;"
                "FBLC/ru_RU;FBOP/5",
                False,
            ),
        ],
    )
    def test_hardcoded_regression(self, user_agent, expected):
        assert is_crawler(user_agent) is expected


class TestInvalidInputs:
    @pytest.mark.parametrize("bad_input", [None, 123, b"test"])
    def test_rejects_non_string(self, bad_input):
        with pytest.raises((AttributeError, TypeError)):
            is_crawler(bad_input)  # type: ignore[arg-type]


class TestFixtureLists:
    def test_sizes(self):
        assert len(load_user_agents(BROWSER_UA_FILE)) == 15864
        assert len(load_user_agents(CRAWLER_UA_FILE)) == 1248

    @pytest.mark.parametrize("user_agent", load_user_agents(BROWSER_UA_FILE))
    def test_browser_not_flagged_as_crawler(self, user_agent):
        assert is_crawler(user_agent) is False

    @pytest.mark.parametrize("user_agent", load_user_agents(CRAWLER_UA_FILE))
    def test_crawler_detected(self, user_agent):
        assert is_crawler(user_agent) is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([str(Path(__file__).resolve())]))
