#!/usr/bin/env python3
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from subprocess import run


def get_latest_version(package: str) -> str | None:
    result = run(
        ["cargo", "info", package],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return None

    for line in result.stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("version:"):
            match = re.search(r'version:\s+([0-9][^\s(]*)', line)
            if not match:
                continue
            version = match.group(1)
            unstable = ("alpha", "beta", "rc", "pre", "dev")
            if not any(marker in version.lower() for marker in unstable):
                return version
    return None


def parse_version(version: str) -> tuple[int | str, ...]:
    cleaned = re.sub(r"^[^0-9]+", "", version)
    return tuple(int(p) if p.isdigit() else p for p in cleaned.split("."))


def extract_version(line: str) -> tuple[str, str, str, bool] | None:
    if "=" not in line:
        return None

    name, rest = line.split("=", 1)
    name = name.strip()
    rest = rest.strip()

    if rest.startswith('"'):
        match = re.search(r'"([^"]+)"', rest)
        if not match:
            return None
        version_string = match.group(1)
        specifier_match = re.match(r"^[^0-9]+", version_string)
        specifier = specifier_match.group(0) if specifier_match else ""
        version = version_string[len(specifier):]
        return name, version, specifier, False

    if rest.startswith("{"):
        match = re.search(r'version\s*=\s*"([^"]+)"', rest)
        if not match:
            return None
        version_string = match.group(1)
        specifier_match = re.match(r"^[^0-9]+", version_string)
        specifier = specifier_match.group(0) if specifier_match else ""
        version = version_string[len(specifier):]
        return name, version, specifier, True

    return None


def simplify_version(version: str) -> str:
    """Simplify version to major.minor for 0.x or major for 1.x+"""
    parts = version.split('.')
    if not parts:
        return version
    
    try:
        major = int(parts[0])
        if major == 0 and len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return parts[0]
    except (ValueError, IndexError):
        return version


def update_line(line: str, new_version: str, specifier: str, is_table: bool) -> str:
    simplified = simplify_version(new_version)
    new_string = f"{specifier}{simplified}"
    if is_table:
        return re.sub(
            r'version\s*=\s*"[^"]+"',
            f'version = "{new_string}"',
            line,
            count=1
        )
    return re.sub(r'"[^"]+"', f'"{new_string}"', line, count=1)


def check_update(line: str) -> tuple[str, str, str, str]:
    parsed = extract_version(line)
    if not parsed:
        return line, "", "", ""

    name, current, specifier, is_table = parsed
    latest = get_latest_version(name)
    if not latest:
        return line, name, current, ""

    simplified_latest = simplify_version(latest)
    
    if parse_version(latest) > parse_version(current):
        updated = update_line(line, latest, specifier, is_table)
        return updated, name, current, simplified_latest
    elif current != simplified_latest:
        updated = update_line(line, latest, specifier, is_table)
        return updated, name, current, simplified_latest

    return line, "", "", ""


def main() -> None:
    cargo_file = Path("Cargo.toml")
    if not cargo_file.exists():
        print("Error: Cargo.toml not found")
        return

    lines = cargo_file.read_text(encoding="utf-8").splitlines(keepends=True)

    in_deps = False
    indices = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[dependencies]":
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            break
        if in_deps and stripped and not stripped.startswith("#"):
            indices.append(i)

    if not indices:
        print("No dependencies found")
        return

    results = {}
    count = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(check_update, lines[i]): i for i in indices}
        for future in as_completed(futures):
            idx = futures[future]
            new_line, name, old, new = future.result()
            results[idx] = new_line
            if new:
                print(f"Updated {name}: {old} -> {new}")
                count += 1
            elif old and not new:
                print(f"Warning: Could not get version for {name}")

    if count:
        for idx, new_line in results.items():
            lines[idx] = new_line
        cargo_file.write_text("".join(lines), encoding="utf-8")
        print(f"\nUpdated {count} package(s)")
    else:
        print("All packages are up to date")


if __name__ == "__main__":
    main()
