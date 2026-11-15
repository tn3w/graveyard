#!/usr/bin/env python3
"""Generate per-crawler SEO pages, robots.txt, sitemap.xml from crawlers.json."""

from __future__ import annotations

from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DIST = ROOT / "dist"
TEMPLATE_PATH = DOCS / "_crawler-template.html"
BLOCKS_PATH = DOCS / "data" / "crawler-block-percentages.json"
LATEST_NAME = "crawler-block-latest.json"
SOURCE_FILES = ("index.html", "404.html", "CNAME")
SITE = "https://crawlerdex.tn3w.dev"


def name_of(pattern: str) -> str:
    s = pattern
    s = re.sub(r"\\([\\/.\-+*?^$|(){}\[\]])", r"\1", s)

    def bracket(match: re.Match[str]) -> str:
        inner = match.group(1)
        upper = re.search(r"[A-Z]", inner)
        if upper:
            return upper.group(0)
        letter = re.search(r"[a-z]", inner)
        if letter:
            return letter.group(0)
        return inner[0] if inner else ""

    def paren(match: re.Match[str]) -> str:
        inner = re.sub(r"^\?[:!=<]", "", match.group(1))
        return inner.split("|")[0] or ""

    s = re.sub(r"\[([^\]]+)\]", bracket, s)
    s = re.sub(r"\(([^)]*)\)", paren, s)
    s = re.sub(r"[()|^$]", "", s)
    s = re.sub(r"[*+?]\??", "", s)
    s = re.sub(r"\{\d+(,\d*)?\}", "", s)
    s = re.sub(r"\\[bBwWsSdD]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[/\-_]+$", "", s).strip()
    return s or pattern


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return slug or "crawler"


def initials(name: str) -> str:
    parts = [p for p in re.split(r"[\s\-_]+", name) if p]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    match = re.match(r"^(?:https?://)?(?:www\.)?([^/]+)", url)
    return match.group(1) if match else None


def fmt_pct(value: float) -> str:
    decimals = 3 if value < 0.001 else 2 if value < 0.01 else 1
    return f"{value * 100:.{decimals}f}"


def block_key(crawler: dict, name: str, blocks: dict) -> str | None:
    pattern = crawler.get("pattern", "")
    instances = (crawler.get("instances") or [])[:3]
    for candidate in [pattern, name, *instances]:
        if candidate in blocks:
            return candidate
        lower = candidate.lower()
        for key in blocks:
            if key.lower() == lower:
                return key
    needle = name.lower().split(" ")[0]
    if len(needle) < 3:
        return None
    for key in blocks:
        if needle in key.lower():
            return key
    return None


def chart_svg(series: dict[str, float]) -> str:
    points = sorted((int(t), v) for t, v in series.items())
    if not points:
        return ""
    width, height, pad = 820, 160, 28
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmin = xs[0]
    xmax = xs[-1] if xs[-1] != xs[0] else xs[0] + 1
    ymax = max(max(ys), 0.001) * 1.15

    def x_at(t: int) -> float:
        if xmax == xmin:
            return pad + (width - pad * 2) * 0.5
        return pad + (width - pad * 2) * (t - xmin) / (xmax - xmin)

    def y_at(v: float) -> float:
        return height - pad - (height - pad * 2) * (v / ymax)

    path = " ".join(
        f"{'L' if i else 'M'}{x_at(p[0]):.1f},{y_at(p[1]):.1f}"
        for i, p in enumerate(points)
    )
    area = f"{path} L{x_at(xmax):.1f},{height - pad} L{x_at(xmin):.1f},{height - pad} Z"
    grid_lines = "".join(
        f'<line class="grid-l" x1="{pad}" x2="{width - pad}" '
        f'y1="{pad + (height - pad * 2) * f}" '
        f'y2="{pad + (height - pad * 2) * f}"/>'
        for f in (0, 0.25, 0.5, 0.75, 1)
    )
    last = len(points) - 1
    dots = "".join(
        f'<circle class="{"latest" if i == last else "dot"}" '
        f'cx="{x_at(p[0]):.1f}" cy="{y_at(p[1]):.1f}" '
        f'r="{5 if i == last else 3}"/>'
        for i, p in enumerate(points)
    )

    def fmt_date(timestamp: int) -> str:
        return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()

    labels = (
        f'<text class="axis" x="{pad}" y="{height - 6}">{fmt_date(xmin)}</text>'
        f'<text class="axis" x="{width - pad}" y="{height - 6}" '
        f'text-anchor="end">{fmt_date(xmax)}</text>'
        f'<text class="axis" x="{pad}" y="{pad - 6}">{fmt_pct(ymax)}%</text>'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'{grid_lines}<path class="area" d="{area}"/>'
        f'<path class="line" d="{path}"/>{dots}{labels}</svg>'
    )


def chart_section(crawler: dict, name: str, blocks: dict) -> str:
    key = block_key(crawler, name, blocks)
    if not key:
        return '<div class="nodata">No block-rate data for this crawler.</div>'
    series = blocks[key]
    if not series:
        return '<div class="nodata">No block-rate data for this crawler.</div>'
    latest_ts = max(int(t) for t in series)
    latest = series[str(latest_ts)] if str(latest_ts) in series else series[latest_ts]
    date = datetime.fromtimestamp(latest_ts, timezone.utc).date().isoformat()
    return (
        '<div class="chart"><div class="top">'
        f'<div class="big">{fmt_pct(latest)}<small>%</small></div>'
        f'<div class="meta-r">latest snapshot<br>{date}<br>'
        f"matched key: {html.escape(key)}</div></div>"
        f"{chart_svg({str(t): v for t, v in series.items()})}</div>"
    )


def load_blocks() -> dict[str, dict[str, float]]:
    if not BLOCKS_PATH.exists():
        return {}
    data = json.loads(BLOCKS_PATH.read_text())
    if "timestamps" not in data:
        return data
    timestamps = data["timestamps"]
    return {
        pattern: {str(ts): v for ts, v in zip(timestamps, row) if v is not None}
        for pattern, row in data["series"].items()
    }


def write_latest(blocks: dict[str, dict[str, float]]) -> None:
    latest = {}
    for pattern, series in blocks.items():
        if series:
            timestamp = max(series, key=int)
            latest[pattern] = [int(timestamp), series[timestamp]]
    (DIST / "data").mkdir(exist_ok=True)
    (DIST / "data" / LATEST_NAME).write_text(json.dumps(latest, separators=(",", ":")))


def htaccess_pattern(pattern: str) -> str:
    return pattern.replace('"', '\\"')


def nginx_pattern(pattern: str) -> str:
    return pattern.replace("\\", "\\\\").replace('"', '\\"')


def fill(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def build_values(crawler: dict, name: str, slug: str, blocks: dict) -> dict[str, str]:
    pattern = crawler.get("pattern", "")
    description = crawler.get("description") or f"{name} web crawler user-agent details."
    tags = crawler.get("tags") or ["uncategorized"]
    instances = crawler.get("instances") or []
    url = crawler.get("url")
    added = crawler.get("addition_date")

    canonical = f"{SITE}/{quote(slug)}"
    title = f"{name} crawler — user-agent, pattern & block-rate · Crawlerdex"
    seo_desc = (
        f"{name}: {description} Detection regex, real User-Agent strings, "
        f"category tags, and live block-rate across the top 25 000 sites."
    )[:300]
    keywords = ", ".join(
        [
            name,
            f"{name} bot",
            f"{name} crawler",
            f"{name} user agent",
            f"{name} user-agent",
            f"is {name} a bot",
            f"block {name}",
            f"{name} robots.txt",
            *tags,
        ]
    )

    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": f"{name} web crawler",
            "description": seo_desc,
            "about": {
                "@type": "SoftwareApplication",
                "name": name,
                "applicationCategory": "WebCrawler",
                "operatingSystem": "Any",
                "url": url or canonical,
            },
            "keywords": keywords,
            "url": canonical,
            "isPartOf": {
                "@type": "WebSite",
                "name": "Crawlerdex",
                "url": SITE,
            },
        },
        indent=2,
    )

    domain = domain_of(url)
    favicon = f"https://icons.duckduckgo.com/ip3/{domain}.ico" if domain else ""
    icon_html = (
        f'<img src="{favicon}" alt="" width="64" height="64" '
        f'loading="lazy" decoding="async" '
        f"onerror=\"this.parentNode.textContent='{html.escape(initials(name))}'\">"
        if favicon
        else html.escape(initials(name))
    )

    instances_html = "".join(
        f'<div class="instance">{html.escape(i)}</div>' for i in instances[:20]
    ) or (
        '<div class="instance" style="opacity:.6;font-style:italic">'
        "no public sample user-agents recorded.</div>"
    )
    extra_instances = (
        f'<p class="more">+ {len(instances) - 20} more samples in '
        f'<a href="https://github.com/tn3w/Crawlerdex/blob/master/crawlers.json">'
        f"crawlers.json</a></p>"
        if len(instances) > 20
        else ""
    )

    tags_html = "".join(
        f'<a class="tag-mini" href="/?tag={quote(t)}">{html.escape(t)}</a>' for t in tags
    )

    ref_row = (
        f'<dt>Reference</dt><dd><a href="{html.escape(url)}" '
        f'rel="noopener" target="_blank">{html.escape(url)}</a></dd>'
        if url
        else ""
    )
    added_row = f"<dt>Added</dt><dd>{html.escape(added)}</dd>" if added else ""

    rdns = crawler.get("rdns") or []
    rdns_row = (
        "<dt>rDNS suffixes</dt><dd>"
        + ", ".join(f"<code>{html.escape(r)}</code>" for r in rdns)
        + "</dd>"
        if rdns
        else ""
    )
    rdns_section = (
        "<h2>rDNS verification (FCrDNS)</h2>"
        f'<p style="font-size:16px;line-height:1.6">Verify a request is genuinely '
        f"<strong>{html.escape(name)}</strong> with forward-confirmed reverse DNS: "
        f"the client IP's PTR record must end in one of the suffixes below "
        f"<strong>and</strong> a forward A/AAAA lookup of that hostname must return "
        f"the same IP. UA strings alone are spoofable; FCrDNS is not.</p>"
        "<ul style=\"font-family:'JetBrains Mono',monospace;font-size:14px;"
        'line-height:1.8;padding-left:20px">'
        + "".join(f"<li><code>{html.escape(r)}</code></li>" for r in rdns)
        + "</ul>"
        if rdns
        else ""
    )

    return {
        "TITLE": html.escape(title),
        "SEO_DESC": html.escape(seo_desc),
        "KEYWORDS": html.escape(keywords),
        "CANONICAL": canonical,
        "JSON_LD": json_ld,
        "NAME": html.escape(name),
        "PATTERN": html.escape(pattern),
        "DESCRIPTION": html.escape(description),
        "TAGS_TEXT": html.escape(", ".join(tags)),
        "TAGS_HTML": tags_html,
        "ICON": icon_html,
        "INSTANCES_HTML": instances_html,
        "EXTRA_INSTANCES": extra_instances,
        "INSTANCE_COUNT": str(len(instances)),
        "REF_ROW": ref_row,
        "ADDED_ROW": added_row,
        "RDNS_ROW": rdns_row,
        "RDNS_SECTION": rdns_section,
        "CHART_SECTION": chart_section(crawler, name, blocks),
        "HTACCESS_PATTERN": html.escape(htaccess_pattern(pattern)),
        "NGINX_PATTERN": html.escape(nginx_pattern(pattern)),
    }


def write_robots(entries: list[tuple[str, str]]) -> None:
    lines = [
        "# Crawlerdex — bot bestiary",
        "# All crawlers welcome. We catalogue you, we don't fight you.",
        "",
        "User-agent: *",
        "Allow: /",
        "",
    ]
    for _, slug in entries:
        lines.append("User-agent: *")
        lines.append(f"Allow: /{slug}")
        lines.append("")
    lines.append(f"Sitemap: {SITE}/sitemap.xml")
    lines.append("")
    (DIST / "robots.txt").write_text("\n".join(lines))


def write_sitemap(entries: list[tuple[str, str]]) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    urls = [
        f"<url><loc>{SITE}/</loc><lastmod>{today}</lastmod>"
        f"<changefreq>daily</changefreq><priority>1.0</priority></url>"
    ]
    for _, slug in entries:
        urls.append(
            f"<url><loc>{SITE}/{quote(slug)}</loc>"
            f"<lastmod>{today}</lastmod>"
            f"<changefreq>weekly</changefreq><priority>0.7</priority></url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    (DIST / "sitemap.xml").write_text(body)


def main() -> int:
    crawlers = json.loads((ROOT / "crawlers.json").read_text())
    template = TEMPLATE_PATH.read_text()
    blocks = load_blocks()

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    for name in SOURCE_FILES:
        src = DOCS / name
        if src.exists():
            shutil.copy2(src, DIST / name)

    data_src = DOCS / "data"
    if data_src.exists():
        shutil.copytree(data_src, DIST / "data")

    write_latest(blocks)

    seen: set[str] = set()
    entries: list[tuple[str, str]] = []
    for crawler in crawlers:
        name = name_of(crawler["pattern"])
        slug = slugify(name)
        original = slug
        counter = 2
        while slug in seen:
            slug = f"{original}-{counter}"
            counter += 1
        seen.add(slug)
        page = fill(template, build_values(crawler, name, slug, blocks))
        (DIST / f"{slug}.html").write_text(page)
        entries.append((name, slug))

    write_robots(entries)
    write_sitemap(entries)
    inject_index_links(entries)
    print(f"generated {len(entries)} crawler pages → dist/")
    return 0


def inject_index_links(entries: list[tuple[str, str]]) -> None:
    index_path = DIST / "index.html"
    text = index_path.read_text()
    placeholder = "<!--CRAWLER_LINKS-->"
    if placeholder not in text:
        return
    links = "\n                ".join(
        f'<li><a href="/{quote(slug)}">{html.escape(name)}</a></li>'
        for name, slug in entries
    )
    index_path.write_text(text.replace(placeholder, links))


if __name__ == "__main__":
    sys.exit(main())
