#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import crua
from crua import (
    BrowserInfo,
    CrawlerExplanation,
    CrawlerInfo,
    UserAgent,
    __all__,
    __version__,
    explain_crawler,
    extract_user_agents,
    is_browser,
    is_crawler,
    normalize_user_agent,
    parse,
    parse_browser,
    parse_crawler,
    parse_or_none,
    safe_parse,
)
from crua.api import _looks_like_user_agent
from crua.crawler import (
    _has_browser_override,
    _has_compat_extension,
    _has_vendor_comment_url,
)
from crua.regex import compile_pattern, findall


class TestPublicExports:
    def test_all_contains_public_api(self):
        assert __all__ == [
            "BrowserInfo",
            "CrawlerExplanation",
            "CrawlerInfo",
            "UserAgent",
            "__version__",
            "explain_crawler",
            "extract_user_agents",
            "is_browser",
            "is_crawler",
            "normalize_user_agent",
            "parse",
            "parse_or_none",
            "parse_browser",
            "parse_crawler",
            "safe_parse",
        ]

    def test_version_string(self):
        assert __version__ == "1.0.9"


class TestConvenienceHelpers:
    def test_extract_user_agents_from_plain_user_agent(self):
        assert extract_user_agents(
            "Googlebot/2.1 (+http://www.google.com/bot.html)"
        ) == ["Googlebot/2.1 (+http://www.google.com/bot.html)"]

    def test_extract_user_agents_from_plain_crawler_client(self):
        assert extract_user_agents("curl/8.7.1") == ["curl/8.7.1"]

    def test_extract_user_agents_from_plain_browser_user_agent(self):
        assert extract_user_agents(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ) == [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ]

    def test_extract_user_agents_from_access_log_line(self):
        line = (
            "127.0.0.1 - - [08/Apr/2026:12:00:00 +0000] "
            '"GET / HTTP/1.1" 200 123 "-" '
            '"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"'
        )

        assert extract_user_agents(line) == [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        ]

    def test_extract_user_agents_from_multiple_lines(self):
        blob = "\n".join(
            [
                '10.0.0.1 - - [08/Apr/2026:12:00:00 +0000] "GET /a HTTP/1.1" 200 1 "-" "curl/8.7.1"',
                '10.0.0.2 - - [08/Apr/2026:12:00:01 +0000] "GET /b HTTP/1.1" 200 1 "-" '
                '"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/135.0.0.0 Safari/537.36"',
            ]
        )

        assert extract_user_agents(blob) == [
            "curl/8.7.1",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36",
        ]

    def test_extract_user_agents_from_random_wrapping_text(self):
        blob = (
            "Hx1pLxzeQHG1ZmWCsrXIBTjlSaLmBFKQ"
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
            "Mobile/15E148 Safari/604.1"
            "VMgx6RMrppNB5TwWyXepW34VEOcKMoy4"
        )

        assert extract_user_agents(blob) == [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
            "Mobile/15E148 Safari/604.1"
        ]

    def test_extract_user_agents_from_sentence_with_crawler(self):
        blob = (
            "Really cool user agent: "
            "AdsBot-Google (+http://www.google.com/adsbot.html)"
            " isnt it?"
        )

        assert extract_user_agents(blob) == [
            "AdsBot-Google (+http://www.google.com/adsbot.html)"
        ]

    def test_extract_user_agents_from_single_quoted_value(self):
        line = (
            "user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'"
        )

        assert extract_user_agents(line) == [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]

    def test_extract_user_agents_ignores_empty_and_non_matches(self):
        blob = '\n\nINFO request_id=1 "GET /health HTTP/1.1" 200\n'

        assert extract_user_agents(blob) == []

    def test_parse_crawler_returns_info_for_crawler(self):
        crawler = parse_crawler("Googlebot/2.1 (+http://www.google.com/bot.html)")

        assert crawler == CrawlerInfo(
            name="Googlebot",
            version="2.1",
            url="http://www.google.com/bot.html",
        )

    def test_parse_crawler_returns_none_for_browser(self):
        crawler = parse_crawler(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )

        assert crawler is None

    def test_parse_browser_returns_browser_info(self):
        browser = parse_browser(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )

        assert browser == BrowserInfo(
            product_token="Mozilla/5.0",
            comment="(Windows NT 10.0; Win64; x64)",
            engine="Blink",
            engine_version="537.36",
            browser="Chrome",
            browser_version="135.0.0.0",
            os="Windows",
            os_version="10/11",
            device="Desktop",
            rendering="KHTML, like Gecko",
        )

    def test_is_browser_is_inverse_of_is_crawler(self):
        crawler_ua = "Googlebot/2.1 (+http://www.google.com/bot.html)"
        browser_ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )

        assert is_crawler(crawler_ua) is True
        assert is_browser(crawler_ua) is False
        assert is_crawler(browser_ua) is False
        assert is_browser(browser_ua) is True

    def test_normalize_user_agent_collapses_whitespace(self):
        assert (
            normalize_user_agent("  Mozilla/5.0 \n\t Chrome/135.0   Safari/537.36  ")
            == "Mozilla/5.0 Chrome/135.0 Safari/537.36"
        )

    def test_normalize_user_agent_handles_non_string_inputs(self):
        assert normalize_user_agent(b"curl/8.7.1\r\n") == "curl/8.7.1"
        assert normalize_user_agent(123) == "123"
        assert normalize_user_agent(None) == ""

    def test_parse_or_none_returns_normalized_result(self):
        parsed = parse_or_none(" \n curl/8.7.1 \t ")

        assert parsed == UserAgent(
            raw="curl/8.7.1",
            is_crawler=True,
            crawler=CrawlerInfo(name="curl", version="8.7.1", url=None),
            browser=BrowserInfo(
                product_token="curl/8.7.1",
                comment=None,
                engine=None,
                engine_version=None,
                browser=None,
                browser_version=None,
                os=None,
                os_version=None,
                device="Desktop",
                rendering=None,
            ),
        )

    def test_parse_or_none_returns_none_for_empty_input(self):
        assert parse_or_none(" \n\t ") is None

    def test_safe_parse_is_alias(self):
        assert safe_parse(
            "Googlebot/2.1 (+http://www.google.com/bot.html)"
        ) == parse_or_none("Googlebot/2.1 (+http://www.google.com/bot.html)")

    def test_explain_crawler_reports_matches(self):
        explanation = explain_crawler(
            "Mozilla/5.0 Chrome/110.0 Safari/537.36 Chrome-Lighthouse"
        )

        assert explanation == CrawlerExplanation(
            raw="Mozilla/5.0 Chrome/110.0 Safari/537.36 Chrome-Lighthouse",
            normalized="Mozilla/5.0 Chrome/110.0 Safari/537.36 Chrome-Lighthouse",
            is_crawler=True,
            matched=["browser_crawler_token"],
            excluded=[],
        )

    def test_explain_crawler_reports_browser_override(self):
        explanation = explain_crawler(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
            "AppleWebKit/605.1.15 Mobile/15E148 FBAN/FBIOS"
        )

        assert explanation.is_crawler is False
        assert explanation.matched == []
        assert explanation.excluded == ["browser_override"]


class TestSerialization:
    def test_crawler_info_to_dict(self):
        crawler = CrawlerInfo(name="Googlebot", version="2.1", url="http://example.com")

        assert crawler.to_dict() == {
            "name": "Googlebot",
            "version": "2.1",
            "url": "http://example.com",
        }

    def test_browser_info_to_dict(self):
        browser = BrowserInfo(
            product_token="Mozilla/5.0",
            comment="(X11; Linux x86_64)",
            engine="Blink",
            engine_version="537.36",
            browser="Chrome",
            browser_version="135.0.0.0",
            os="Linux",
            os_version=None,
            device="Desktop",
            rendering="KHTML, like Gecko",
        )

        assert browser.to_dict() == {
            "product_token": "Mozilla/5.0",
            "comment": "(X11; Linux x86_64)",
            "engine": "Blink",
            "engine_version": "537.36",
            "browser": "Chrome",
            "browser_version": "135.0.0.0",
            "os": "Linux",
            "os_version": None,
            "device": "Desktop",
            "rendering": "KHTML, like Gecko",
        }

    def test_user_agent_to_dict(self):
        user_agent = parse(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        )

        assert user_agent.to_dict() == {
            "raw": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "is_crawler": False,
            "crawler": None,
            "browser": {
                "product_token": "Mozilla/5.0",
                "comment": "(Windows NT 10.0; Win64; x64)",
                "engine": "Blink",
                "engine_version": "537.36",
                "browser": "Chrome",
                "browser_version": "135.0.0.0",
                "os": "Windows",
                "os_version": "10/11",
                "device": "Desktop",
                "rendering": "KHTML, like Gecko",
            },
        }

    def test_user_agent_to_dict_with_crawler(self):
        user_agent = UserAgent(
            raw="Googlebot/2.1 (+http://www.google.com/bot.html)",
            is_crawler=True,
            crawler=CrawlerInfo(
                name="Googlebot",
                version="2.1",
                url="http://www.google.com/bot.html",
            ),
            browser=None,
        )

        assert user_agent.to_dict() == {
            "raw": "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "is_crawler": True,
            "crawler": {
                "name": "Googlebot",
                "version": "2.1",
                "url": "http://www.google.com/bot.html",
            },
            "browser": None,
        }

    def test_crawler_explanation_to_dict(self):
        explanation = CrawlerExplanation(
            raw="curl/8.7.1",
            normalized="curl/8.7.1",
            is_crawler=True,
            matched=["non_browser_product"],
            excluded=[],
        )

        assert explanation.to_dict() == {
            "raw": "curl/8.7.1",
            "normalized": "curl/8.7.1",
            "is_crawler": True,
            "matched": ["non_browser_product"],
            "excluded": [],
        }


class TestAdditionalBranches:
    def test_findall_flattens_tuple_matches(self):
        pattern = compile_pattern(r"(foo)(bar)")

        assert findall(pattern, "foobar") == ["foo"]

    def test_compat_extension_detected_as_crawler(self):
        assert is_crawler("Mozilla/5.0 (compatible; Foo; Bar; ExtraToken)") is True

    def test_compat_extension_rejects_lowercase_tail(self):
        assert (
            _has_compat_extension("Mozilla/5.0 (compatible; Foo; Bar; lowercase)")
            is False
        )

    def test_vendor_comment_url_requires_closed_comment(self):
        assert (
            _has_vendor_comment_url(
                "Mozilla/5.0 Safari/537.36 (Checkly, https://checkly.example"
            )
            is False
        )

    def test_moatbot_browser_override_branch(self):
        assert (
            _has_browser_override(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/40.0.2214.111 Safari/537.36 moatbot"
            )
            is True
        )

    def test_suspicious_x11_vendor_detected_as_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (X11; WeirdCorp; Linux x86_64) " "AppleWebKit/537.36"
            )
            is True
        )

    def test_browser_word_short_circuits_non_mozilla_product(self):
        assert is_crawler("Mystery Browser Agent") is False

    def test_looks_like_user_agent_rejects_blank(self):
        assert _looks_like_user_agent("   ") is False

    def test_looks_like_user_agent_accepts_mozilla_style_crawler(self):
        assert _looks_like_user_agent("Mozilla/5.0 AppInsights") is True
