#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crua import parse


class TestSimpleProductToken:
    def test_name_version_url(self):
        result = parse("MyBot/2.3 (+http://example.com)")
        assert result.crawler is not None
        assert result.crawler.name == "MyBot"
        assert result.crawler.version == "2.3"
        assert result.crawler.url == "http://example.com"

    def test_no_version_without_slash(self):
        result = parse("SimpleCrawler")
        assert result.crawler is not None
        assert result.crawler.name == "SimpleCrawler"
        assert result.crawler.version is None

    def test_url_none_when_absent(self):
        result = parse("MyBot/1.0")
        assert result.crawler is not None
        assert result.crawler.url is None

    def test_first_url_when_multiple(self):
        result = parse("Bot/1.0 (+http://first.com) extra http://second.com")
        assert result.crawler is not None
        assert result.crawler.url == "http://first.com"


class TestCompatBlock:
    def test_name_version_url(self):
        result = parse("Mozilla/5.0 (compatible; MyCrawler/3.1; +http://example.com)")
        assert result.crawler is not None
        assert result.crawler.name == "MyCrawler"
        assert result.crawler.version == "3.1"
        assert result.crawler.url == "http://example.com"


class TestFreeTokenScan:
    def test_name_from_non_known_token(self):
        result = parse("Mozilla/5.0 AppInsights")
        assert result.crawler is not None
        assert result.crawler.name == "AppInsights"

    def test_name_after_comment_strip(self):
        result = parse("Mozilla/5.0 (Windows NT 10.0) AppInsights")
        assert result.crawler is not None
        assert result.crawler.name == "AppInsights"

    def test_version_with_slash(self):
        result = parse("Mozilla/5.0 (Windows NT 10.0) 360Spider/1.0")
        assert result.crawler is not None
        assert result.crawler.name == "360Spider"
        assert result.crawler.version == "1.0"

    def test_fallback_none_when_all_tokens_known(self):
        result = parse("Mozilla/5.0")
        assert result.crawler is not None
        assert result.crawler.name is None


if __name__ == "__main__":
    import pytest as _pytest

    raise SystemExit(_pytest.main([str(Path(__file__).resolve())]))
