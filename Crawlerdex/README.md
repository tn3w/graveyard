# 🕷️ Crawlerdex

> the bestiary of bots

**2900+ crawler user-agents.** Detection regex, real UA samples, rDNS verification, live block-rates. → [crawlerdex.tn3w.dev](https://crawlerdex.tn3w.dev)

Download:

```
https://github.com/tn3w/Crawlerdex/releases/latest/download/crawlers.json                    # full
https://github.com/tn3w/Crawlerdex/releases/latest/download/crawlers.min.json                # no instances, no addition_date, minified (~57% smaller)
https://github.com/tn3w/Crawlerdex/releases/latest/download/crawler-stats.json               # per-crawler aggregate block-rate stats
https://github.com/tn3w/Crawlerdex/releases/latest/download/crawler-block-percentages.json   # block-rate time series, columnar (see below)
https://github.com/tn3w/Crawlerdex/releases/latest/download/domain-crawler-blocks.json       # per-domain allow/block map
```

---

## Entry shape

```jsonc
{
  "pattern": "Googlebot\\/", // regex tested against User-Agent
  "description": "Google search indexing bot",
  "tags": ["search-engine"], // 1+ from the whitelist
  "instances": ["Googlebot/2.1 (+http://www.google.com/bot.html)", "..."],
  "url": "https://www.google.com/bot.html", // optional, official docs
  "addition_date": "2017/08/21", // optional, YYYY/MM/DD
  "depends_on": ["heritrix"], // optional, parent libs
  "rdns": [".google.com", ".googlebot.com"], // optional, FCrDNS suffixes
}
```

`rdns` = forward-confirmed reverse-DNS suffixes. A bot is genuine only when its IP rDNS ends in one of these **and** a forward lookup returns the same IP.

## Tags

| Tag                  | Block risk  |                            |
| -------------------- | ----------- | -------------------------- |
| `search-engine`      | Low         | web search indexing        |
| `ai-crawler`         | High        | autonomous AI training     |
| `ai-fetcher`         | Varies      | user-prompted single fetch |
| `social-preview`     | Low         | link previews              |
| `seo`                | Medium      | SEO / backlink analysis    |
| `monitoring`         | Low         | uptime / health probes     |
| `feed-reader`        | Low         | RSS / Atom                 |
| `archiver`           | Low         | preservation               |
| `advertising`        | Low/Medium  | ad quality, conversion     |
| `scanner`            | High        | security / vuln scanners   |
| `http-library`       | Medium/High | generic HTTP clients       |
| `browser-automation` | Medium/High | headless browsers          |
| `academic`           | Low         | research crawlers          |

## Frontend

`docs/` = source (`index.html`, `404.html`, `_crawler-template.html`, `CNAME`). `tools/build_pages.py` reads template + `docs/data/` → emits per-crawler pages, `robots.txt`, `sitemap.xml`, copies sources into `dist/`. Pages deploy from `dist/`. rDNS suffixes shown in modal + per-crawler page (FCrDNS section). Block-rate produced by `tools/radar.py`.

```bash
mkdir -p docs/data && cp crawlers.json docs/data/
python3 tools/build_pages.py
python3 -m http.server -d dist
```

## Block-rate radar

`tools/radar.py` fetches Tranco top-N×1000 `robots.txt`, parses allow/disallow per UA, accumulates block-rate stats and time series.

```bash
pip install httpx
python3 tools/radar.py
```

Flags: `--top-thousands` (default 25), `--max-workers` (512), `--timeout` (3s).
Outputs (minified JSON): `crawler-stats.json`, `crawler-block-percentages.json`, `domain-crawler-blocks.json`.

`crawler-block-percentages.json` is columnar: `{"timestamps": [...], "series": {pattern: [value | null, ...]}}`. Values align with `timestamps`; `null` = no sample, trailing `null`s are trimmed. ~50% smaller than the old `{pattern: {timestamp: value}}` layout, which radar still reads.

## Validation

`tools/validate.py`: schema, types, tag whitelist, ReDoS (static + dynamic 50 ms probe), pattern/instance match, cross-matches, browser smoke test (~30k real + 2000 synthetic UAs), canonical formatting.

```bash
python3 tools/validate.py
```

Stats summary printed after every run. Exit `1` on any error.

## Format & lint

```bash
python3 -m venv .venv && .venv/bin/pip install ruff
.venv/bin/ruff format . && .venv/bin/ruff check --fix .
npx --yes prettier --write --single-quote --print-width=100 --trailing-comma=es5 --end-of-line=lf "**/*.{md,yml,yaml,html,css,js,ts}"
```

## Social banner

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install Pillow
python banner.py
```

## CI

- `release-crawlers.yml` — push to `crawlers.json` / `tools/radar.py`, daily cron, or manual: rebuild `crawlers.min.json`, run radar, publish all artifacts as a GitHub release. Keeps last 5.
- `deploy-pages.yml` — runs after a successful release (also on `docs/` changes or manual): pulls `crawler-block-percentages.json` from latest release, builds + minifies pages, writes `data/crawler-block-latest.json` (`{pattern: [timestamp, value]}`, ~200 KB), deploys to GitHub Pages. The index page loads only the latest file; the full series loads on first detail open.

## Credits

Forked from [monperrus/crawler-user-agents](https://github.com/monperrus/crawler-user-agents).
