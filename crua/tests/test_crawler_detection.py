#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from crua import is_crawler, parse
from crua.crawler import (
    _has_browser_override,
    _has_compat_extension,
    _has_suspicious_x11_vendor,
    _has_vendor_comment_url,
)


class TestBrowserCrawlerTokens:
    @pytest.mark.parametrize(
        "ua",
        [
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/110.0 Safari/537.36 Chrome-Lighthouse",
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0; AppInsights)",
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0) 360Spider",
            "Mozilla/5.0 Chrome/110.0 Safari/537.36 LinkCheck by example.com",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/40.0.2214.111 Safari/537.36 moatbot",
        ],
    )
    def test_detected_as_crawler(self, ua):
        assert is_crawler(ua) is True


class TestBrowserOverrides:
    def test_fban_fbios(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                "AppleWebKit/605.1.15 Mobile/15E148 FBAN/FBIOS"
            )
            is False
        )

    def test_sleipnir(self):
        assert is_crawler("Sleipnir/2.9.9 (compatible; Windows NT 6.1)") is False

    def test_konqueror_exabot_thumbnails(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (compatible; Konqueror/3.5; Linux) "
                "KHTML/3.5.10 (like Gecko) (Exabot-Thumbnails)"
            )
            is False
        )

    def test_xbox_agent(self):
        assert (
            is_crawler("Mozilla/5.0 (Windows NT 10.0; Win64; x64; Xbox One)-agent")
            is False
        )

    def test_msie_trident_not_ending_paren(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0) extra"
            )
            is False
        )

    def test_moatbot_direct(self):
        assert (
            _has_browser_override(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/40.0.2214.111 Safari/537.36 moatbot"
            )
            is True
        )


class TestBotSignals:
    def test_bot_word(self):
        assert is_crawler("MyBot/1.0") is True

    def test_spider_word(self):
        assert is_crawler("MySpider/2.0 (+http://example.com)") is True

    def test_email_in_ua(self):
        assert is_crawler("Crawler support@example.com") is True

    def test_www_contact_url(self):
        assert is_crawler("Crawler www.example.com") is True

    def test_chrome_fake_version(self):
        assert is_crawler("Mozilla/5.0 Chrome/ABC") is True


class TestContactMarker:
    def test_plus_http_triggers(self):
        assert is_crawler("Mozilla/5.0 (Windows NT 10.0; +http://example.com)") is True

    def test_compat_plus_http_at(self):
        assert (
            is_crawler("Mozilla/5.0 (compatible; +http://example.com bot@example.com)")
            is True
        )


class TestCompatExtension:
    def test_few_parts_returns_false(self):
        assert _has_compat_extension("SomeUA (compatible; A; B)") is False

    def test_empty_tail(self):
        assert (
            parse("Mozilla/5.0 (compatible; CustomA; CustomB; CustomC; )").is_crawler
            is True
        )

    def test_short_tail(self):
        assert (
            parse("Mozilla/5.0 (compatible; CustomA; CustomB; CustomC; AB)").is_crawler
            is True
        )

    def test_lowercase_tail(self):
        assert (
            parse(
                "Mozilla/5.0 (compatible; CustomA; CustomB; CustomC; lowercase)"
            ).is_crawler
            is True
        )

    def test_non_alpha_tail(self):
        assert (
            parse(
                "Mozilla/5.0 (compatible; CustomA; CustomB; CustomC; Brand1)"
            ).is_crawler
            is True
        )

    def test_valid_tail_detected(self):
        assert (
            parse(
                "Mozilla/5.0 (compatible; CustomA; CustomB; CustomC; BrandName)"
            ).is_crawler
            is True
        )


class TestHeadlessShell:
    def test_headless_chrome_is_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "HeadlessChrome/112.0.0.0 Safari/537.36"
            )
            is True
        )

    def test_headless_chrome_with_edge_is_not_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 AppleWebKit/537.36 HeadlessChrome/112.0 Safari/537.36 Edg/112.0"
            )
            is False
        )


class TestVendorCommentUrl:
    def test_detected_as_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 "
                "Safari/537.36 (Checkly, https://www.checklyhq.com)"
            )
            is True
        )

    def test_no_safari_firefox_not_triggered(self):
        assert _has_vendor_comment_url("Mozilla/5.0 (https://example.com)") is False

    def test_no_closing_paren_not_triggered(self):
        assert is_crawler("Mozilla/5.0 Safari/537.36 (https://example.com") is False


class TestSuspiciousX11Vendor:
    def test_unknown_vendor_is_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (X11; CustomVendor; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/100.0.0.0 Safari/537.36"
            )
            is True
        )

    def test_u_vendor_skipped(self):
        assert (
            _has_suspicious_x11_vendor(
                "Mozilla/5.0 (X11; U; Linux x86_64) AppleWebKit/537.36"
            )
            is False
        )

    def test_known_distro_not_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/100.0.0.0 Safari/537.36"
            )
            is False
        )


class TestSuffixHeuristics:
    def test_uppercase_acronym_suffix(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 "
                "Chrome/110.0 Safari/537.36 PTST/211202"
            )
            is True
        )

    def test_long_suffix_is_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 "
                "Chrome/100.0 Safari/537.36 MySpecialAuditingThing/1234"
            )
            is True
        )

    def test_long_browser_shaped_suffix_not_crawler(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 "
                "Chrome/100.0.0.0 Safari/537.36 MyBigCustomBrowser/2.0"
            )
            is False
        )

    def test_suspicious_trailing_label(self):
        assert (
            is_crawler(
                "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 "
                "Chrome/100.0.0.0 Safari/537.36 SomeTrailingLabel"
            )
            is True
        )


class TestMozillaFallback:
    def test_mozilla_without_browser_tokens_is_crawler(self):
        assert is_crawler("Mozilla/5.0 (compatible)") is True

    def test_non_mozilla_with_browser_token_not_crawler(self):
        assert is_crawler("Lynx/2.8.9 (compatible; Chrome/110.0)") is False

    def test_browser_slash_not_crawler(self):
        assert is_crawler("SomeName Browser/2.0") is False

    def test_browser_space_not_crawler(self):
        assert is_crawler("SomeName Browser 2.0") is False


class TestParseOptions:
    def test_crawlers_false_skips_detection(self):
        result = parse(
            "Googlebot/2.1 (+http://www.google.com/bot.html)", crawlers=False
        )
        assert result.is_crawler is False
        assert result.crawler is None


if __name__ == "__main__":
    import pytest as _pytest

    raise SystemExit(_pytest.main([str(Path(__file__).resolve())]))
