import pytest

import is_crawler
from is_crawler import ip, parser

GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
CHROME = (
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36"
)
GOOGLE_ADDRESS = "66.249.66.1"
UNKNOWN_ADDRESS = "203.0.113.7"


def test_detection_wraps_uaid():
    assert is_crawler.is_crawler(GOOGLEBOT)
    assert not is_crawler.is_crawler(CHROME)
    assert is_crawler.crawler_name(GOOGLEBOT) == "Googlebot"
    assert is_crawler.crawler_name(CHROME) == "Chrome"
    assert is_crawler.crawler_version(GOOGLEBOT) == "2.1"
    assert is_crawler.crawler_url(GOOGLEBOT) == "http://www.google.com/bot.html"
    assert is_crawler.crawler_url(CHROME) is None
    assert is_crawler.crawler_contact("Bot/1.0 (ops@example.com)") == "ops@example.com"
    assert is_crawler.crawler_match(GOOGLEBOT) == "bot"
    assert is_crawler.crawler_match(CHROME) is None
    assert is_crawler.crawler_signals(GOOGLEBOT) == [
        "bot_signal",
        "known_tool",
        "url_in_ua",
    ]
    assert is_crawler.crawler_signals("curl/8.4.0") == [
        "bot_signal",
        "no_browser_signature",
        "known_tool",
    ]


def test_database_wraps_uaid():
    info = is_crawler.crawler_info(GOOGLEBOT)
    assert info.tags == ("search-engine",) and ".googlebot.com" in info.rdns
    assert is_crawler.crawler_info(CHROME) is None
    assert is_crawler.assert_crawler(GOOGLEBOT) == info
    with pytest.raises(ValueError):
        is_crawler.assert_crawler(CHROME)
    assert is_crawler.is_search_engine(GOOGLEBOT)
    assert is_crawler.is_good_crawler(GOOGLEBOT)
    assert not is_crawler.is_bad_crawler(GOOGLEBOT)
    assert is_crawler.is_http_library("curl/8.4.0")
    assert not is_crawler.crawler_has_tag(CHROME, "search-engine")


@pytest.mark.parametrize(
    "check",
    [
        is_crawler.is_ai_crawler,
        is_crawler.is_ai_fetcher,
        is_crawler.is_seo,
        is_crawler.is_social_preview,
        is_crawler.is_advertising,
        is_crawler.is_archiver,
        is_crawler.is_feed_reader,
        is_crawler.is_monitoring,
        is_crawler.is_scanner,
        is_crawler.is_academic,
        is_crawler.is_browser_automation,
    ],
)
def test_tag_checks_reject_googlebot(check):
    assert not check(GOOGLEBOT)


def test_custom_crawlers_take_precedence():
    is_crawler.register_crawler("acme", r"AcmeBot/\d", description="Acme", tags=["seo"])
    assert is_crawler.crawler_info("AcmeBot/1").description == "Acme"
    assert is_crawler.unregister_crawler("acme")
    assert not is_crawler.unregister_crawler("acme")
    with is_crawler.custom_crawlers({"name": "x", "pattern": "XBot", "tags": ["seo"]}):
        assert is_crawler.is_seo("XBot")
    assert is_crawler.crawler_info("XBot") is None
    is_crawler.register_crawler("y", "YBot")
    is_crawler.clear_custom_crawlers()
    assert is_crawler.crawler_info("YBot") is None


def test_iter_crawlers_lists_database_entries():
    crawlers = list(is_crawler.iter_crawlers())
    assert len(crawlers) > 4000
    assert any(name == "googlebot" for _, name in crawlers)


def test_robots_and_ai_txt():
    assert "gptbot" in is_crawler.robots_agents_for_tags("ai-crawler")
    text = is_crawler.build_robots_txt(
        disallow="ai-crawler",
        allow="search-engine",
        rules=[("/private/", ["seo"])],
    )
    assert "User-agent: gptbot\n" in text and "Allow: /\n" in text
    assert text.endswith("Disallow: /private/\n")
    assert is_crawler.build_robots_txt() == ""
    assert is_crawler.build_ai_txt().startswith("User-Agent: ")


def test_ip_checks_use_bundled_networks():
    assert ip.ip_in_range(GOOGLE_ADDRESS)
    assert ip.known_crawler_ip(f" {GOOGLE_ADDRESS} ")
    assert not ip.ip_in_range("not an ip")
    assert ip.known_crawler_rdns(GOOGLE_ADDRESS)
    assert not ip.known_crawler_rdns("not an ip")
    assert ip.verify_crawler_ip(GOOGLEBOT, GOOGLE_ADDRESS)
    assert not ip.verify_crawler_ip(GOOGLEBOT, "not an ip")


def fake_dns(monkeypatch, host, addresses):
    ip.uaid.confirmed.cache_clear()
    infos = [(2, 1, 6, "", (address, 0)) for address in addresses]
    monkeypatch.setattr(ip.socket, "gethostbyaddr", lambda address: (host, [], []))
    monkeypatch.setattr(ip.socket, "getaddrinfo", lambda name, port: infos)


def test_dns_checks(monkeypatch):
    fake_dns(monkeypatch, "Crawl.GoogleBot.com.", [UNKNOWN_ADDRESS])
    assert ip.reverse_dns(UNKNOWN_ADDRESS) == "crawl.googlebot.com"
    assert ip.reverse_dns("not an ip") is None
    suffixes = (".googlebot.com",)
    assert ip.forward_confirmed_rdns(UNKNOWN_ADDRESS, suffixes) == "crawl.googlebot.com"
    assert ip.forward_confirmed_rdns("not an ip", suffixes) is None
    assert ip.known_crawler_rdns(UNKNOWN_ADDRESS)
    assert ip.verify_crawler_ip(GOOGLEBOT, UNKNOWN_ADDRESS)


def test_dns_failures(monkeypatch):
    def fail(*arguments):
        raise OSError

    ip.uaid.confirmed.cache_clear()
    monkeypatch.setattr(ip.socket, "gethostbyaddr", fail)
    assert ip.reverse_dns(UNKNOWN_ADDRESS) is None
    assert not ip.known_crawler_rdns(UNKNOWN_ADDRESS)


def test_parser_wraps_uaid():
    found = parser.parse(CHROME)
    assert (found.browser, found.browser_major, found.os, found.device) == (
        "Chrome",
        "120",
        "Android",
        "Mobile",
    )
    assert found.is_mobile and not found.is_tablet and not found.is_crawler
    assert (found.device_brand, found.device_model) == ("Samsung", "SM-S918B")
    assert found.product_token == "Mozilla/5.0"
    assert found.comment == "(Linux; Android 14; SM-S918B)"
    assert found.rendering == "KHTML, like Gecko"
    assert found.to_dict()["browser"] == "Chrome"
    assert parser.parse("curl/8.4.0").rendering is None
    assert parser.parse("Foo (KHTML)").rendering == "KHTML"
    assert parser.parse("").product_token is None


def test_parser_flags_apps_webviews_and_headless():
    instagram = parser.parse(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Mobile/15E148 Instagram 309.0.0.40.113"
    )
    assert instagram.app == "Instagram" and instagram.is_webview
    headless = parser.parse("Mozilla/5.0 (X11) HeadlessChrome/120.0.0.0 Safari/537.36")
    assert headless.is_headless and headless.is_crawler


def test_parser_helpers():
    assert parser.normalize_user_agent(b"  a \n b ") == "a b"
    assert parser.normalize_user_agent(None) == ""
    assert parser.normalize_user_agent(12) == "12"
    assert parser.parse_or_none("") is None
    assert parser.parse_or_none(CHROME).browser == "Chrome"
    assert parser.is_crawler(GOOGLEBOT) and not parser.is_browser(GOOGLEBOT)
