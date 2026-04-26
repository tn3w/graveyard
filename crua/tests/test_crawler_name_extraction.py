#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from crua import parse

TESTS_DIR = Path(__file__).resolve().parent
CRAWLER_NAMES_FILE = TESTS_DIR / "fixtures" / "crawler_names.json"


def load_crawler_names() -> dict[str, list[str]]:
    return json.loads(CRAWLER_NAMES_FILE.read_text(encoding="utf-8"))


def iter_first_instances(crawler_names: dict[str, list[str]]) -> list[tuple[str, str]]:
    return [
        (expected_name, instances[0])
        for expected_name, instances in crawler_names.items()
        if instances
    ]


class TestFixtureShape:
    def test_expected_shape(self):
        crawler_names = load_crawler_names()

        assert len(crawler_names) >= 400
        assert all(isinstance(name, str) and name for name in crawler_names)
        assert all(
            isinstance(instances, list) and instances
            for instances in crawler_names.values()
        )
        assert all(
            isinstance(instance, str) and instance
            for instances in crawler_names.values()
            for instance in instances
        )


class TestCrawlerDetection:
    @pytest.mark.parametrize(
        ("expected_name", "user_agent"),
        iter_first_instances(load_crawler_names()),
    )
    def test_detected_as_crawler(self, expected_name, user_agent):
        result = parse(user_agent)
        assert result.is_crawler is True, expected_name
        assert result.crawler is not None, expected_name


class TestNameExtraction:
    def test_all_fixture_names_match(self):
        crawler_names = load_crawler_names()
        mismatches: list[tuple[str, str | None, str]] = []

        for expected_name, user_agents in crawler_names.items():
            for user_agent in user_agents:
                result = parse(user_agent)
                actual_name = (
                    result.crawler.name if result.crawler is not None else None
                )
                if actual_name != expected_name:
                    mismatches.append((expected_name, actual_name, user_agent))

        assert mismatches == [], "\n".join(
            [
                "Crawler name extraction mismatches:",
                *[
                    f"expected={expected!r} actual={actual!r} ua={ua!r}"
                    for expected, actual, ua in mismatches[:25]
                ],
            ]
        )

    @pytest.mark.parametrize(
        ("fixture_name", "index", "expected_version", "expected_url"),
        [
            ("Googlebot", 0, "2.1", "http://www.google.com/bot.html"),
            ("AddSearchBot", 0, "0.9", "http://www.addsearch.com/bot"),
            ("ChatGPT-User", 0, "1.0", "https://openai.com/bot"),
            ("DataForSeoBot", 0, "1.0", "https://dataforseo.com/dataforseo-bot"),
            ("MJ12bot", 0, "v1.2.0", "http://majestic12.co.uk/bot.php?+"),
            ("PetalBot", 0, None, "https://webmaster.petalsearch.com/site/petalbot"),
            ("Apache-HttpClient", 0, "4.2.3", None),
            ("Claude-SearchBot", 0, None, None),
        ],
    )
    def test_version_and_url(self, fixture_name, index, expected_version, expected_url):
        user_agent = load_crawler_names()[fixture_name][index]
        result = parse(user_agent)
        assert result.crawler is not None
        assert result.crawler.version == expected_version
        assert result.crawler.url == expected_url


class TestBrowserShapedCrawlers:
    def test_keeps_browser_metadata(self):
        user_agent = load_crawler_names()["AmazonProductDiscovery"][0]
        result = parse(user_agent)

        assert result.is_crawler is True
        assert result.crawler is not None
        assert result.crawler.name == "AmazonProductDiscovery"
        assert result.browser is not None
        assert result.browser.browser == "Chrome"
        assert result.browser.browser_version == "110.0.0.0"
        assert result.browser.os == "Linux"
        assert result.browser.device == "Desktop"


if __name__ == "__main__":
    raise SystemExit(pytest.main([str(Path(__file__).resolve())]))
