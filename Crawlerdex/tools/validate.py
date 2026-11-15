#!/usr/bin/env python3
"""Validate crawlers.json. Run: python3 tools/validate.py"""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import re
import sys
import time
import warnings

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "crawlers.json"
BROWSER_UAS = Path(__file__).resolve().parent / "browser_uas.txt"

ALLOWED_TAGS = {
    "search-engine",
    "ai-crawler",
    "ai-fetcher",
    "social-preview",
    "seo",
    "monitoring",
    "feed-reader",
    "archiver",
    "advertising",
    "scanner",
    "http-library",
    "browser-automation",
    "academic",
}
REQUIRED_KEYS = {"pattern", "description", "tags", "instances"}
ALLOWED_KEYS = REQUIRED_KEYS | {"url", "addition_date", "depends_on", "rdns"}
KEY_ORDER = ["pattern", "url", "instances", "description", "tags", "addition_date", "depends_on", "rdns"]
EXCLUSIVE_TAG_GROUPS = [{"ai-crawler", "ai-fetcher"}]

DATE_RE = re.compile(r"^\d{4}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])$")
RDNS_RE = re.compile(
    r"^\.[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
)
CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
REDOS_HEURISTICS = [
    re.compile(r"\([^)]*[+*][^)]*\)[+*]"),
    re.compile(r"(\[[^\]]+\]|\.|\\w|\\d|\\s)[+*]\1[+*]"),
    re.compile(r"\(\?:[^)]*\|[^)]*\)[+*]\{"),
]
PERF_HEURISTICS = [
    (re.compile(r"\.\*[A-Za-z_]{3,}"), "use [^/]* or specific prefix instead of .*"),
    (re.compile(r"\.\+[A-Za-z_]{3,}"), "use [^/]+ or specific prefix instead of .+"),
    (re.compile(r"(?<![\\])\.\*\.\*"), "consecutive .* is redundant"),
]
TOO_PERMISSIVE = {".*", ".+", ".", r"\w+", r"\w*", r"\S+", r"\S*", r"\b\w+\b"}
MIN_LITERAL_CHARS = 3
MAX_PATTERN_LEN = 120
MAX_INSTANCE_LEN = 300
MAX_DESCRIPTION_CHARS = 100
MAX_DESCRIPTION_WORDS = 10
MAX_URL_LEN = 400
PATTERN_BUDGET = 0.05
REDOS_PROBE = "A" * 5000 + "!"

FRAMEWORK_PARENTS = {
    "Go-http-client",
    "HeadlessChrome",
    "AppEngine-Google",
    "Googlebot\\/",
    "WordPress",
    "libwww-perl",
    "heritrix",
    "Nutch",
    "Verity\\/",
    "BW\\/",
    "Dark Visitor",
    "UptimeBot\\/",
    "mail\\.ru",
    "SputnikBot",
}

errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def literal_chars(pattern: str) -> int:
    s = re.sub(r"\\[bBwWsSdDnrtfv]", "", pattern)
    s = re.sub(r"\\.", "X", s)
    s = re.sub(r"\[[^\]]*\]", "X", s)
    s = re.sub(r"\(\?[:!=<][^)]*\)", "", s)
    return len(re.sub(r"[()|^$.*+?{}]", "", s))


def derive_name(pattern: str) -> str:
    s = re.sub(r"\\([\\\/.\-+*?^$|(){}\[\]])", r"\1", pattern)
    s = re.sub(r"\[([^\]]+)\]", lambda m: m.group(1)[0], s)
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[*+?{}]", "", s).strip(" /-_")


def check_str(i: int, label: str, val, max_len: int | None = None) -> bool:
    if not isinstance(val, str) or not val.strip():
        err(f"[{i}] {label} must be non-empty string")
        return False
    if val != val.strip():
        err(f"[{i}] {label} has leading/trailing whitespace")
    if CTRL_RE.search(val):
        err(f"[{i}] {label} has control characters")
    if max_len and len(val) > max_len:
        err(f"[{i}] {label} too long ({len(val)} > {max_len} chars)")
    return True


def validate_tags(i: int, tags) -> None:
    if not isinstance(tags, list) or not tags:
        err(f"[{i}] tags must be non-empty list")
        return
    for t in tags:
        if not isinstance(t, str):
            err(f"[{i}] tag not a string: {t!r}")
        elif t not in ALLOWED_TAGS:
            err(f"[{i}] unknown tag {t!r}")
    if len(tags) != len(set(tags)):
        err(f"[{i}] duplicate tags in {tags}")
    for group in EXCLUSIVE_TAG_GROUPS:
        present = group & set(tags)
        if len(present) > 1:
            err(f"[{i}] mutually-exclusive tags both set: {sorted(present)}")


def validate_instances(i: int, instances) -> None:
    if not isinstance(instances, list):
        err(f"[{i}] instances must be list")
        return
    for j, s in enumerate(instances):
        if isinstance(s, str) and s:
            check_str(i, f".instances[{j}]", s, max_len=MAX_INSTANCE_LEN)
        else:
            err(f"[{i}].instances[{j}] not non-empty string")
    strs = [s for s in instances if isinstance(s, str)]
    if len(strs) != len(set(strs)):
        err(f"[{i}] duplicate instance strings")


def validate_url(i: int, url) -> None:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        err(f"[{i}] url must be http(s) string")
        return
    if url != url.strip():
        err(f"[{i}] url has whitespace")
    if len(url) > MAX_URL_LEN:
        err(f"[{i}] url too long ({len(url)} > {MAX_URL_LEN} chars)")


def validate_date(i: int, added) -> None:
    if not isinstance(added, str) or not DATE_RE.match(added):
        err(f"[{i}] addition_date must match YYYY/MM/DD: {added!r}")
        return
    try:
        dt = datetime.strptime(added, "%Y/%m/%d").date()
    except ValueError:
        err(f"[{i}] addition_date not a real date: {added!r}")
        return
    if dt < date(2000, 1, 1) or dt > date.today():
        err(f"[{i}] addition_date implausible: {added}")


def validate_rdns(i: int, rdns) -> None:
    if not isinstance(rdns, list) or not rdns:
        err(f"[{i}] rdns must be non-empty list")
        return
    for j, suf in enumerate(rdns):
        if not isinstance(suf, str) or not RDNS_RE.match(suf):
            err(f"[{i}].rdns[{j}] invalid suffix {suf!r}")
    if list(rdns) != sorted(rdns):
        warn(f"[{i}] rdns not sorted")
    if len(rdns) != len(set(rdns)):
        err(f"[{i}] duplicate rdns suffixes")
    strs = [s for s in rdns if isinstance(s, str)]
    for suf in strs:
        for other in strs:
            if suf != other and suf.endswith(other):
                err(f"[{i}] rdns {suf!r} is redundant, already covered by {other!r}")


def validate_entry(i: int, e: dict) -> None:
    keys = set(e.keys())
    if missing := REQUIRED_KEYS - keys:
        err(f"[{i}] missing keys: {sorted(missing)}")
    if unknown := keys - ALLOWED_KEYS:
        err(f"[{i}] unknown keys: {sorted(unknown)}")

    p = e.get("pattern")
    if not isinstance(p, str) or not p:
        err(f"[{i}] pattern must be non-empty string")
    elif len(p) > MAX_PATTERN_LEN:
        err(f"[{i}] pattern too long ({len(p)} > {MAX_PATTERN_LEN} chars)")

    desc = e.get("description")
    if check_str(i, "description", desc, max_len=MAX_DESCRIPTION_CHARS) and isinstance(desc, str):
        if len(desc.split()) > MAX_DESCRIPTION_WORDS:
            err(f"[{i}] description too long ({len(desc.split())} > {MAX_DESCRIPTION_WORDS} words)")
    validate_tags(i, e.get("tags"))
    validate_instances(i, e.get("instances"))

    if (url := e.get("url")) is not None:
        validate_url(i, url)
    if (added := e.get("addition_date")) is not None:
        validate_date(i, added)
    if (rdns := e.get("rdns")) is not None:
        validate_rdns(i, rdns)

    deps = e.get("depends_on")
    if deps is not None and (
        not isinstance(deps, list) or not all(isinstance(s, str) and s for s in deps)
    ):
        err(f"[{i}] depends_on must be list of non-empty strings")


def validate_schema(entries: list) -> None:
    if not isinstance(entries, list):
        err("root must be a JSON array")
        return
    for i, e in enumerate(entries):
        if isinstance(e, dict):
            validate_entry(i, e)
        else:
            err(f"[{i}] not an object")


def check_pattern(i: int, p: str, compiled: re.Pattern) -> None:
    if p in TOO_PERMISSIVE:
        err(f"[{i}] pattern matches too much: {p!r}")
        return
    if (lits := literal_chars(p)) < MIN_LITERAL_CHARS:
        err(f"[{i}] pattern has {lits} literal chars (<{MIN_LITERAL_CHARS}): {p!r}")
    if any(rx.search(p) for rx in REDOS_HEURISTICS):
        err(f"[{i}] pattern looks ReDoS-prone: {p!r}")
    for rx, hint in PERF_HEURISTICS:
        if rx.search(p):
            err(f"[{i}] pattern inefficient ({hint}): {p!r}")
            break
    started = time.perf_counter()
    try:
        compiled.search(REDOS_PROBE)
    except Exception:
        pass
    else:
        elapsed = time.perf_counter() - started
        if elapsed > PATTERN_BUDGET:
            err(f"[{i}] pattern slow ({elapsed * 1000:.0f}ms): {p!r}")
    if p.startswith("^") and p.endswith("$"):
        warn(f"[{i}] pattern fully anchored: {p!r}")
    if re.search(r"\\([a-zA-Z0-9])", p) and not re.search(r"\\[bBwWsSdDnrtfv]", p):
        warn(f"[{i}] possibly redundant escape: {p!r}")
    if re.search(r"\\/\d[\d\\.]*", p):
        err(f"[{i}] pattern contains hardcoded version number: {p!r}")


def validate_patterns(entries: list) -> list:
    out: list[tuple[int, dict, re.Pattern]] = []
    seen: dict[str, int] = {}
    for i, e in enumerate(entries):
        p = e.get("pattern")
        if not isinstance(p, str):
            continue
        if p in seen:
            err(f"[{i}] duplicate pattern of [{seen[p]}]: {p!r}")
            continue
        seen[p] = i
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", SyntaxWarning)
                compiled = re.compile(p)
        except SyntaxWarning as ex:
            err(f"[{i}] pattern has invalid escape sequence: {p!r} ({ex})")
            continue
        except re.error as ex:
            err(f"[{i}] pattern does not compile: {p!r} ({ex})")
            continue
        try:
            re.compile("(?:" + p + ")")
        except re.error as ex:
            err(f"[{i}] pattern not pipe-compatible: {p!r} ({ex})")
        out.append((i, e, compiled))
        check_pattern(i, p, compiled)
    return out


def validate_pattern_instances(compiled: list) -> None:
    for i, e, p in compiled:
        for j, ins in enumerate(e.get("instances") or []):
            if isinstance(ins, str) and not p.search(ins):
                err(
                    f"[{i}] {e['pattern']!r} does not match own instance[{j}]: "
                    f"{ins[:120]}"
                )


def validate_cross_matches(compiled: list) -> None:
    for i, e, p in compiled:
        for ins in e.get("instances") or []:
            if not isinstance(ins, str):
                continue
            own = p.search(ins)
            if not own:
                continue
            own_span = own.end() - own.start()
            for j, e2, p2 in compiled:
                if j == i:
                    continue
                other = p2.search(ins)
                if not other or (other.end() - other.start()) <= own_span:
                    continue
                if (
                    e2["pattern"] in FRAMEWORK_PARENTS
                    or e["pattern"] in FRAMEWORK_PARENTS
                ):
                    continue
                err(
                    f"[{i}] {e['pattern']!r} owned instance matched more strongly by "
                    f"[{j}] {e2['pattern']!r}: {ins[:120]}"
                )


def validate_depends_on(entries: list) -> None:
    patterns = {e.get("pattern") for e in entries if isinstance(e.get("pattern"), str)}
    derived = {derive_name(p).lower() for p in patterns}
    for i, e in enumerate(entries):
        for dep in e.get("depends_on") or []:
            if dep == e.get("pattern"):
                err(f"[{i}] depends_on references its own pattern")
            elif dep not in patterns and dep.lower() not in derived:
                warn(f"[{i}] depends_on {dep!r} not found")


def validate_browser_safety(compiled: list) -> None:
    if not BROWSER_UAS.exists():
        return
    pool = [line.strip() for line in BROWSER_UAS.read_text().splitlines() if line.strip()]
    print(f"browser smoke test against {len(pool)} UAs...")
    for i, e, p in compiled:
        for ua in pool:
            if p.search(ua):
                err(f"[{i}] {e['pattern']!r} matches real browser UA: {ua[:120]!r}")
                break


def print_stats(entries: list) -> None:
    print("\n=== stats ===")
    print(f"entries: {len(entries)}")
    by_tag: dict[str, int] = {}
    for e in entries:
        for t in e.get("tags") or []:
            by_tag[t] = by_tag.get(t, 0) + 1
    for tag, n in sorted(by_tag.items(), key=lambda x: -x[1]):
        print(f"  {tag:20s} {n:5d}")
    print(f"  with url:           {sum(1 for e in entries if e.get('url'))}")
    print(f"  with rdns:          {sum(1 for e in entries if e.get('rdns'))}")
    print(f"  with addition_date: {sum(1 for e in entries if e.get('addition_date'))}")
    print(f"  without instances:  {sum(1 for e in entries if not e.get('instances'))}")
    counts = sorted(len(e.get("instances") or []) for e in entries)
    if counts:
        print(f"  instances/entry:    median={counts[len(counts) // 2]} max={counts[-1]}")
    print()


def main() -> int:
    raw = PATH.read_text()
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as ex:
        print(f"crawlers.json is not valid JSON: {ex}", file=sys.stderr)
        return 1

    print(f"validating {len(entries)} entries from {PATH.relative_to(ROOT)}\n")
    validate_schema(entries)
    compiled = validate_patterns(entries)
    validate_pattern_instances(compiled)
    validate_cross_matches(compiled)
    validate_depends_on(entries)
    ordered = [{k: e[k] for k in KEY_ORDER if k in e} for e in entries]
    canonical = json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"
    if raw != canonical:
        PATH.write_text(canonical)
        print("crawlers.json reformatted to canonical form")
    validate_browser_safety(compiled)
    print_stats(entries)

    for w in warns:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERR   {e}")
    print(f"\nerrors:   {len(errors)}\nwarnings: {len(warns)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
