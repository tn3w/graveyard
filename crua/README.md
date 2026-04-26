<p align="center">
  <img src="https://raw.githubusercontent.com/tn3w/crua/screenshot/crua.webp" alt="CRUA banner" width="500px">
</p>

<p align="center">
  <a href="https://pypi.org/project/crua/">
    <img src="https://img.shields.io/pypi/v/crua?style=for-the-badge" alt="PyPI Version">
  </a>
  <a href="https://github.com/tn3w/crua/actions/workflows/publish.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/tn3w/crua/publish.yml?label=Publish&style=for-the-badge" alt="Publish Status">
  </a>
  <a href="https://github.com/tn3w/crua/blob/master/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache--2.0-0f766e?style=for-the-badge" alt="License">
  </a>
</p>

<h3 align="center">Fast crawler detection and browser parsing for Python.</h3>

<p align="center">
  Built for the common question every backend eventually asks:
  <br>
  <strong>is this traffic a real browser, or some kind of bot?</strong>
</p>

## Why CRUA?

CRUA gives you a small API for classifying user agents, extracting browser metadata, and debugging crawler matches when something looks off.

<table>
  <tr>
    <td><strong>Fast</strong><br>Regex-driven and lightweight.</td>
    <td><strong>Practical</strong><br>Focused on real app and log processing needs.</td>
    <td><strong>Debuggable</strong><br><code>explain_crawler()</code> shows why something matched.</td>
  </tr>
</table>

## Install

```bash
pip install crua
```

Optional faster regex backend:

```bash
pip install google-re2
```

## Quick Start

```python
from crua import explain_crawler, is_crawler, parse

ua = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

result = parse(ua)

result.is_crawler         # False
result.browser.browser    # "Chrome"
result.browser.os         # "Windows"
result.browser.device     # "Desktop"

is_crawler("Googlebot/2.1 (+http://www.google.com/bot.html)")
# True

explain_crawler("Mozilla/5.0 Chrome/110.0 Safari/537.36 Chrome-Lighthouse").matched
# ["browser_crawler_token"]
```

## API

```python
from crua import (
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
```

| Function                 | What it does                                                      |
| ------------------------ | ----------------------------------------------------------------- |
| `is_crawler()`           | Returns `True` when the user agent should be treated as a crawler |
| `is_browser()`           | Convenience inverse of `is_crawler()`                             |
| `parse()`                | Returns structured crawler and browser metadata                   |
| `parse_crawler()`        | Returns crawler info when the UA is classified as a crawler       |
| `parse_browser()`        | Returns browser, engine, OS, and device info                      |
| `parse_or_none()`        | Defensive parse that returns `None` for empty normalized input    |
| `safe_parse()`           | Alias for `parse_or_none()`                                       |
| `normalize_user_agent()` | Trims and normalizes whitespace before parsing                    |
| `explain_crawler()`      | Returns matched crawler heuristics and exclusions                 |
| `extract_user_agents()`  | Pulls user-agent strings out of text and log blobs                |

## Useful Examples

### Defensive parsing

```python
from crua import safe_parse

safe_parse(b"curl/8.7.1\r\n").crawler.name
# "curl"

safe_parse("   ")
# None
```

### Normalize noisy input

```python
from crua import normalize_user_agent

normalize_user_agent("  Mozilla/5.0 \n Chrome/120.0 Safari/537.36  ")
# "Mozilla/5.0 Chrome/120.0 Safari/537.36"
```

### Extract from logs

```python
from crua import extract_user_agents

line = (
    '127.0.0.1 - - [08/Apr/2026:12:00:00 +0000] '
    '"GET / HTTP/1.1" 200 123 "-" '
    '"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"'
)

extract_user_agents(line)
# ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#  "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"]
```

## Returned Objects

### `UserAgent`

```python
result = parse("Googlebot/2.1 (+http://www.google.com/bot.html)")

result.raw
result.is_crawler
result.crawler
result.browser
```

| Field        | Type                  | Meaning                                  |
| ------------ | --------------------- | ---------------------------------------- |
| `raw`        | `str`                 | Original user-agent string               |
| `is_crawler` | `bool`                | Final crawler classification             |
| `crawler`    | `CrawlerInfo \| None` | Crawler metadata when detected           |
| `browser`    | `BrowserInfo \| None` | Browser, engine, OS, and device metadata |

### `CrawlerInfo`

```python
result = parse("Googlebot/2.1 (+http://www.google.com/bot.html)")

result.crawler.name
result.crawler.version
result.crawler.url
```

| Field     | Type          | Meaning                                          |
| --------- | ------------- | ------------------------------------------------ |
| `name`    | `str \| None` | Crawler family or token name, like `"Googlebot"` |
| `version` | `str \| None` | Parsed crawler version when present              |
| `url`     | `str \| None` | Contact or info URL found in the user agent      |

### `BrowserInfo`

```python
result = parse(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

result.browser.browser
result.browser.browser_version
result.browser.os
result.browser.device
```

| Field             | Type          | Meaning                                                       |
| ----------------- | ------------- | ------------------------------------------------------------- |
| `product_token`   | `str \| None` | First product token, often `"Mozilla/5.0"`                    |
| `comment`         | `str \| None` | First parenthesized comment block                             |
| `engine`          | `str \| None` | Rendering engine, such as `Blink`, `AppleWebKit`, or `Gecko`  |
| `engine_version`  | `str \| None` | Engine version when available                                 |
| `browser`         | `str \| None` | Browser name, such as `Chrome`, `Firefox`, or `Safari`        |
| `browser_version` | `str \| None` | Browser version when available                                |
| `os`              | `str \| None` | Operating system name                                         |
| `os_version`      | `str \| None` | Operating system version when available                       |
| `device`          | `str \| None` | Device class like `Desktop`, `Mobile`, `Tablet`, or `SmartTV` |
| `rendering`       | `str \| None` | Extra rendering hint, for example `KHTML, like Gecko`         |

### `CrawlerExplanation`

```python
explanation = explain_crawler(
    "Mozilla/5.0 Chrome/110.0 Safari/537.36 Chrome-Lighthouse"
)

explanation.is_crawler
explanation.matched
explanation.excluded
```

All returned dataclasses expose `to_dict()`.

## Typical Use Cases

- Filter bots from analytics or rate limiting logic
- Split crawler traffic from browser traffic in logs
- Parse browser, OS, and device info for dashboards
- Debug false positives with `explain_crawler()`
- Safely handle mixed or messy inputs with `safe_parse()`

## Development

```bash
pip install -e .[dev]
pytest
```

## Formatting

```bash
pip install black isort
isort . && black .
npx prtfm
```
