from __future__ import annotations

from .regex import Pattern, compile_pattern

_BOT_WORDS = "bot|crawl|spider|scrape|fetch|scan|index|monitor|preview"
_AUDIT_WORDS = "Check|Match"
_VERSION = r"\d+(?:\.\d+)*"
_PRODUCT_VERSION = r"[\w.-]+"
_APP_BROWSER_TOKENS = (
    "Camino|Fennec|Arora|Epiphany|Firebird|Surf|Iceweasel|OmniWeb|"
    "NetFront|Sleipnir\\d*(?:SiteUpdates)?|QtWeb|TheWorld|GreenBrowser|"
    "Maxthon|ChromePlus|XWEB|WeChat|Weixin|Kazehakase|chromeframe|"
    "MicroMessenger|MQQBrowser"
)
_BROWSER_CRAWLER_TOKENS = (
    "Chrome-Lighthouse|Google-Ads-Conversions|Google Favicon|"
    "AppInsights|360Spider|moatbot"
)
_LONG_SUFFIX_ALLOWLIST = frozenset(
    {
        "MicroMessenger",
        "Snapchat",
        "NetNewsWire",
        "GranParadiso",
        "CravingExplorer",
        "TenFourFox",
        "Waterfox",
        "PaleMoon",
        "YandexSearch",
        "QtWeb",
        "Sleipnir",
        "OmniWeb",
        "NetFront",
        "AviraScout",
        "ChromePlus",
        "TheWorld",
        "Iceweasel",
        "GreenBrowser",
        "XWEB",
        "WeChat",
        "Weixin",
        "MiuiBrowser",
    }
)
_LONG_SUFFIX_ENDINGS: tuple[str, ...] = (
    "browser",
    "mobile",
    "frame",
    "platform",
    "player",
    "messenger",
    "services",
)
_BROWSER_OVERRIDE_SUBSTRINGS: tuple[str, ...] = (
    "FBAN/FBIOS",
    "Sleipnir/",
    "DeskBrowse/",
    "Lunascape",
)
_SIMPLE_VERSIONED_PATTERNS = {
    "webkit_version": ("AppleWebKit", ""),
    "trident_version": ("Trident", ""),
    "presto_version": ("Presto", ""),
    "goanna_version": ("Goanna", ""),
    "opera_mini": ("Opera Mini", ""),
    "opera_mobi": ("Opera Mobi", ""),
    "opera_tablet": ("Opera Tablet", ""),
    "samsung": ("SamsungBrowser", ""),
    "uc_browser": ("UCBrowser", ""),
    "yandex": ("YaBrowser", ""),
    "gsa": ("GSA", ""),
    "crios": ("CriOS", ""),
    "fxios": ("FxiOS", ""),
    "huawei": ("HuaweiBrowser", ""),
    "silk": ("Silk", ""),
    "vivaldi": ("Vivaldi", ""),
    "iron": ("Iron", ""),
    "rockmelt": ("RockMelt", ""),
    "chromium": ("Chromium", ""),
    "chrome": ("Chrome", ""),
    "firefox": ("Firefox", ""),
    "seamonkey": ("SeaMonkey", ""),
    "flock": ("Flock", ""),
    "konqueror": ("Konqueror", ""),
    "iemobile": ("IEMobile", ""),
    "k_meleon": ("K-Meleon", ""),
    "epiphany": ("Epiphany", ""),
    "sleipnir": ("Sleipnir", ""),
    "tesla": ("Tesla", ""),
    "snapchat": ("Snapchat", ""),
    "wechat": ("MicroMessenger", ""),
    "tiktok": ("musically_go", ""),
    "duckduckgo": ("DuckDuckGo", ""),
    "midori": ("Midori", ""),
    "omniweb": ("OmniWeb", ""),
    "waterfox": ("Waterfox", ""),
    "whale": ("Whale", ""),
    "qqbrowser": ("QQBrowser", ""),
    "camino": ("Camino", ""),
    "arora": ("Arora", ""),
    "firebird": ("Firebird", ""),
    "fennec": ("Fennec", ""),
    "mobile_safari": ("Mobile Safari", ""),
}

_PATTERNS: dict[str, str] = {
    "bot_signals": (
        r"(?i)(?:"
        rf"{_BOT_WORDS}|"
        r"(?:^|\s)www\.[^\s/]+\.[A-Za-z]{2,}\b|"
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b|"
        r"-agent\b|"
        r"Chrome/[A-Za-z]|"
        r"\brenderer/\d|"
        r"\bFollowing [A-Za-z][\w\-]+|"
        rf"\b(?:[A-Za-z]+)?(?:{_AUDIT_WORDS})\s+by\s+\S+|"
        r";\s*[A-Z][A-Za-z]+(?:/[0-9][\w.\-]*)?\s*$"
        r")"
    ),
    "browser": (
        r"(?i)(?:"
        rf"(?:Chrome|Chromium|Firefox|Safari|Version|Edg(?:e|A|iOS)?|OPR|"
        rf"SamsungBrowser|CriOS|FxiOS|GSA|HuaweiBrowser|Trident|Presto)/{_VERSION}|"
        rf"Opera(?:\b|[/ ]{_VERSION})|"
        rf"[A-Za-z0-9]+Browser/{_VERSION}|"
        rf"[A-Za-z][\w.-]*browser/{_PRODUCT_VERSION}|"
        rf"[A-Za-z][\w.-]*(?:\s+[A-Za-z][\w.-]*)+\s+Browser/{_PRODUCT_VERSION}|"
        rf"[A-Za-z]+Mobile/{_VERSION}|"
        rf"MSIE {_VERSION}|Konqueror/{_VERSION}|"
        rf"(?:AOL|iCab)\s+{_VERSION}|"
        rf"Netscape(?:6)?/{_VERSION}|"
        rf"(?:{_APP_BROWSER_TOKENS})/{_PRODUCT_VERSION}|"
        rf"(?:Dorothy|pango-text)\b|Tesla/{_PRODUCT_VERSION}|AppleWebKit/\d+|"
        rf"Gecko/\d{{1,8}}|rv:{_VERSION}|Firefox\b|epiphany-browser\b"
        r")"
    ),
    "suspicious_trailing_label": (
        r"(?:Chrome|Firefox)/\d[\w.]*.*Safari/\d[\w.]*\s+"
        r"(?:[A-Z][a-z]+(?:[A-Z][A-Za-z]+)+)\s*$"
    ),
    "browser_crawler": (
        r"(?i)(?:"
        rf"\b(?:{_BROWSER_CRAWLER_TOKENS})\b|"
        r"\b(?:LinkCheck|SiteCheck-[\w-]+)\s+by\s+\S+"
        r")"
    ),
    "url": r"https?://[^\s);,]+",
    "quoted_value": r'"[^"\n]+"|\'[^\'\n]+\'',
    "embedded_browser_ua": (
        rf"Mozilla/\d+(?:\.\d+)?\s*"
        r"\([^)]+\)"
        r"(?:\s+\([^)]+\)|\s+[^\s\"'\n\r]+)*?"
        rf"(?:\s+Firefox/{_VERSION}|"
        rf"\s+Version/{_VERSION}\s+Mobile/[A-Za-z0-9._-]+\s+Safari/{_VERSION}|"
        rf"\s+Version/{_VERSION}\s+Safari/{_VERSION}|"
        rf"\s+Chrome/{_VERSION}\s+Safari/{_VERSION}(?:\s+Edg(?:e|A|iOS)?/{_VERSION}|\s+OPR/{_VERSION})?|"
        rf"\s+Chromium/{_VERSION}\s+Safari/{_VERSION}|"
        rf"\s+IEMobile/{_VERSION}|\s+MSIE {_VERSION}|"
        rf"\s+SamsungBrowser/{_VERSION}|\s+UCBrowser/{_VERSION}|\s+YaBrowser/{_VERSION}|"
        rf"\s+CriOS/{_VERSION}|\s+FxiOS/{_VERSION}|\s+HuaweiBrowser/{_VERSION}|"
        rf"\s+Silk/{_VERSION}|\s+DuckDuckGo/{_VERSION}|\s+Whale/{_VERSION}|\s+QQBrowser/{_VERSION}|"
        rf"\s+MicroMessenger/{_VERSION}|\s+PaleMoon/{_VERSION}|\s+SeaMonkey/{_VERSION}|"
        rf"\s+Konqueror/{_VERSION})"
    ),
    "embedded_crawler_ua": (
        r"(?i)"
        r"(?:"
        r"[A-Za-z][\w.-]*(?:bot|crawl|spider|scrape|fetch|scan|index|monitor|preview)"
        r"[\w.-]*(?:/[^\s\"'()]+)?(?:\s+\([^)]+\))?|"
        r"(?:Chrome-Lighthouse|Google-Ads-Conversions|Google Favicon|AppInsights|360Spider|moatbot)"
        r"(?:/[^\s\"'()]+)?(?:\s+\([^)]+\))?"
        r")"
    ),
    "compatible": r"(?i)compatible;\s*([\w][\w.\-]+)(?:/([\d][\w.\-]*))?",
    "comment_block": r"\([^)]*\)",
    "token_version": r"/([\d][\w.\-]*)",
    "windows_nt": r"(?i)Windows NT (\d+\.\d+)",
    "mac_version": r"Mac OS X (\d+[_.]\d+(?:[_.]\d+)?)",
    "android_version": r"Android (\d+(?:\.\d+)*)",
    "ios_version": r"(?:iPhone OS|CPU OS) (\d+[_]\d+(?:[_]\d+)?)",
    "linux_distro": (
        r"\b(Ubuntu|Fedora|Debian|CentOS|Arch|Mint|SUSE|Red Hat|Gentoo|Kali|"
        r"Raspbian|Slackware|Mageia|Mandriva|OpenSUSE|openSUSE|Kubuntu|Zenwalk)\b"
    ),
    "gecko_version": rf"\bGecko/(\d{{8,}}|{_VERSION})",
    "brave": rf"\b[Bb]rave/({_VERSION})",
    "edge": rf"\bEdg(?:e|A|iOS)?/({_VERSION})",
    "opera": rf"\bOPR/({_VERSION})",
    "opera_legacy": rf"\bOpera[/ ]({_VERSION})",
    "opera_touch": rf"\bOPT/({_VERSION})",
    "palemoon": rf"\bPaleMoon/({_VERSION})",
    "iceweasel": rf"(?i)\biceweasel/({_VERSION})",
    "netscape": rf"\bNetscape/({_VERSION})",
    "netscape_nav": rf"\bNavigator/({_VERSION})",
    "ie_msie": rf"\bMSIE ({_VERSION})",
    "lunascape": rf"\bLunascape[/ ]({_VERSION})",
    "facebook": rf"\b(?:FBAV|FBIOS)/({_VERSION})",
    "instagram": rf"\bInstagram ({_VERSION})",
    "icab": rf"\biCab[/ ]({_VERSION})",
    "maxthon": rf"(?i)\bMaxthon[/ ]({_VERSION})",
    "avant": rf"\bAvant Browser\b",
    "windows_legacy": r"(?i)Windows (?:95|98|CE|ME|3\.\d+|NT\b|[A-Z])",
    "safari_version": rf"\bVersion/({_VERSION})",
    "links": r"(?i)^(?:E?Links)[/ (]",
}

_PATTERNS |= {
    name: rf"\b{token}{spacer}/({_VERSION})"
    for name, (token, spacer) in _SIMPLE_VERSIONED_PATTERNS.items()
}

H: dict[str, Pattern] = {
    name: compile_pattern(pattern) for name, pattern in _PATTERNS.items()
}

KNOWN_TOKENS: frozenset[str] = frozenset(
    {
        "Mozilla",
        "AppleWebKit",
        "Gecko",
        "Chrome",
        "Firefox",
        "Safari",
        "Version",
        "Edge",
        "Edg",
        "EdgA",
        "EdgiOS",
        "OPR",
        "SamsungBrowser",
        "CriOS",
        "FxiOS",
        "GSA",
        "HuaweiBrowser",
        "Trailer",
        "YaBrowser",
        "UCBrowser",
        "Silk",
        "Mobile",
        "Brave",
    }
)

LONG_SUFFIX_ALLOWLIST: frozenset[str] = _LONG_SUFFIX_ALLOWLIST
LONG_SUFFIX_ENDINGS: tuple[str, ...] = _LONG_SUFFIX_ENDINGS
BROWSER_OVERRIDE_SUBSTRINGS: tuple[str, ...] = _BROWSER_OVERRIDE_SUBSTRINGS
