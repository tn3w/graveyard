import os
import re
import time
from pathlib import Path

# --- existence / permissions ---


def exists(path: Path) -> bool:
    """Keep only directories that exist on disk."""
    return path.is_dir()


def writable(path: Path) -> bool:
    """Keep only directories the current user can write to."""
    return path.is_dir() and os.access(path, os.W_OK)


def readable(path: Path) -> bool:
    """Keep only directories the current user can read."""
    return path.is_dir() and os.access(path, os.R_OK)


def is_symlink(path: Path) -> bool:
    """Keep only directories that are symbolic links."""
    return path.is_symlink()


def is_real(path: Path) -> bool:
    """Keep only directories that are not symbolic links."""
    return path.is_dir() and not path.is_symlink()


# --- content ---


def is_empty(path: Path) -> bool:
    """Keep only directories that exist but contain no entries."""
    return path.is_dir() and not any(path.iterdir())


def is_nonempty(path: Path) -> bool:
    """Keep only directories that exist and contain at least one entry."""
    return path.is_dir() and any(path.iterdir())


def has_executables(path: Path) -> bool:
    """Keep only directories that contain at least one executable file."""
    return path.is_dir() and any(
        f.is_file() and os.access(f, os.X_OK) for f in path.iterdir()
    )


def has_executable(name: str):
    """Keep entries that contain an executable file named *name*."""
    return lambda path: (path / name).is_file() and os.access(path / name, os.X_OK)


# --- path structure ---


def depth(n: int):
    """Keep entries whose path has exactly *n* components."""
    return lambda path: len(path.parts) == n


def min_depth(n: int):
    """Keep entries whose path has at least *n* components."""
    return lambda path: len(path.parts) >= n


def max_depth(n: int):
    """Keep entries whose path has at most *n* components."""
    return lambda path: len(path.parts) <= n


def startswith(prefix: str):
    """Keep entries that start with *prefix*."""
    return lambda path: str(path).startswith(prefix)


def contains(substring: str):
    """Keep entries whose string representation contains *substring*."""
    return lambda path: substring in str(path)


def matches(pattern: str):
    """Keep entries whose string representation matches the regex *pattern*."""
    compiled = re.compile(pattern)
    return lambda path: bool(compiled.search(str(path)))


# --- location ---


def is_user(path: Path) -> bool:
    """Keep only entries under the current user's home directory."""
    try:
        path.relative_to(Path.home())
        return True
    except ValueError:
        return False


def is_system(path: Path) -> bool:
    """Keep only entries under common system directories (/usr, /bin, /sbin, etc.)."""
    system_roots = {"/usr", "/bin", "/sbin", "/lib", "/opt", "/etc"}
    return any(str(path).startswith(r) for r in system_roots)


def is_venv(path: Path) -> bool:
    """Keep only entries that are inside a Python virtual environment."""
    return any((p / "pyvenv.cfg").exists() for p in path.parents)


# --- time ---


def newer_than(days: float):
    """Keep entries modified more recently than *days* ago."""
    cutoff = time.time() - days * 86400
    return lambda path: path.is_dir() and path.stat().st_mtime > cutoff


def older_than(days: float):
    """Keep entries not modified within the last *days* days."""
    cutoff = time.time() - days * 86400
    return lambda path: path.is_dir() and path.stat().st_mtime < cutoff


# --- combinators ---


def not_(predicate):
    """Invert a filter predicate."""
    return lambda path: not predicate(path)


def all_(*predicates):
    """Keep entries that satisfy every predicate (logical AND)."""
    return lambda path: all(p(path) for p in predicates)


def any_(*predicates):
    """Keep entries that satisfy at least one predicate (logical OR)."""
    return lambda path: any(p(path) for p in predicates)
