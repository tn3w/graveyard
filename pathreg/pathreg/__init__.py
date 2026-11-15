import argparse
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path

_WINDOWS = sys.platform in ("win32", "cygwin")
_PROFILES = {
    "bash": ("~/.bash_profile", "~/.profile"),
    "sh": ("~/.profile",),
    "zsh": ("~/.zshenv",),
}

if _WINDOWS:
    import ctypes
    import winreg  # type: ignore

    def _reg_path():
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, "Path")[0]

    def _reg_set(value):
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE
        ) as k:
            winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, value)

        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x1A, 0, "Environment", 2, 5000, None
        )


def _profile(shell: str) -> Path:
    """Return the best existing profile file for *shell*, or the first candidate."""
    if shell not in _PROFILES:
        raise NotImplementedError(f"Unsupported shell: {shell}")

    candidates = [Path(c).expanduser() for c in _PROFILES[shell]]
    return next((p for p in candidates if p.exists()), candidates[0])


def _shell() -> str:
    return os.environ.get("SHELL", "").rsplit("/", 1)[-1]


def _entry(directory: str) -> str:
    return f'PATH="{directory}:$PATH"\n'


def _add_path_windows(directory: str, index: int | None = None) -> None:
    """Append *directory* to the user PATH in the Windows registry. Idempotent."""
    directory = directory.strip().replace("/", "\\").removesuffix("\\")

    current = _reg_path()
    parts = current.split(os.pathsep)

    if directory in parts or directory + "\\" in parts:
        return

    if index is None:
        parts.append(directory)
    else:
        parts.insert(index, directory)
    _reg_set(os.pathsep.join(parts))

    env_parts = os.environ.get("PATH", "").split(os.pathsep)
    if index is None:
        env_parts.append(directory)
    else:
        env_parts.insert(index, directory)
    os.environ["PATH"] = os.pathsep.join(env_parts)


def _add_path_unix(directory: str, index: int | None = None) -> None:
    """Insert a PATH entry for *directory* into the shell profile file. Idempotent."""
    directory = directory.strip().replace("\\", "/").removesuffix("/")

    profile = _profile(_shell())
    text = profile.read_text() if profile.exists() else ""

    if _entry(directory) in text:
        return

    entries = [
        m.group(0) for m in re.finditer(r'(?:export )?PATH="[^"]*:\$PATH"\n', text)
    ]
    if index is None:
        entries.append(_entry(directory))
    else:
        entries.insert(index, _entry(directory))

    clean = re.sub(r'(?:export )?PATH="[^"]*:\$PATH"\n', "", text)
    profile.write_text(clean + "".join(entries))

    env_parts = [p for p in os.environ.get("PATH", "").split(":") if p]
    if index is None:
        env_parts.append(directory)
    else:
        env_parts.insert(index, directory)
    os.environ["PATH"] = ":".join(env_parts)


def _remove_path_windows(directory: str) -> None:
    """Remove *directory* from the user PATH in the Windows registry."""
    directory = directory.strip().replace("/", "\\").removesuffix("\\")

    parts = [
        p for p in _reg_path().split(os.pathsep) if p.removesuffix("\\") != directory
    ]
    _reg_set(os.pathsep.join(parts))

    os.environ["PATH"] = os.pathsep.join(
        p
        for p in os.environ.get("PATH", "").split(os.pathsep)
        if p.removesuffix("\\") != directory
    )


def _remove_path_unix(directory: str) -> None:
    """Remove the PATH entry for *directory* from the shell profile file."""
    directory = directory.strip().replace("\\", "/").removesuffix("/")

    profile = _profile(_shell())
    if not profile.exists():
        return

    content = profile.read_text()
    for variant in (f"export {_entry(directory)}", _entry(directory)):
        content = content.replace(variant, "")
    profile.write_text(content)

    os.environ["PATH"] = ":".join(
        p for p in os.environ.get("PATH", "").split(":") if p != directory
    )


def _set_path_windows(directories: list[str]) -> None:
    """Replace the user PATH in the Windows registry with *directories*."""
    normalized = [d.strip().replace("/", "\\").removesuffix("\\") for d in directories]
    _reg_set(os.pathsep.join(normalized))
    os.environ["PATH"] = os.pathsep.join(normalized)


def _set_path_unix(directories: list[str]) -> None:
    """Replace all PATH entries in the shell profile with *directories*."""
    normalized = [d.strip().replace("\\", "/").removesuffix("/") for d in directories]

    profile = _profile(_shell())
    text = profile.read_text() if profile.exists() else ""

    text = re.sub(r'(?:export )?PATH="[^"]*:\$PATH"\n', "", text)
    profile.write_text(text + "".join(_entry(d) for d in normalized))
    os.environ["PATH"] = ":".join(normalized)


add_path: Callable[..., None] = _add_path_windows if _WINDOWS else _add_path_unix
"""Add *directory* to PATH at *index* (default None = append) persistently and in
the current process. Idempotent."""


def prepend_path(directory: str) -> None:
    """Add *directory* to the front of PATH persistently and in the current process."""
    add_path(directory, index=0)


remove_path: Callable[[str], None] = (
    _remove_path_windows if _WINDOWS else _remove_path_unix
)
"""Remove *directory* from PATH persistently and in the current process."""

set_path: Callable[[list[str]], None] = (
    _set_path_windows if _WINDOWS else _set_path_unix
)
"""Replace PATH with *directories* persistently and in the current process."""


def move_path(directory: str, index: int) -> None:
    """Move *directory* to *index* in PATH in the current process.

    No-op if *directory* is not in PATH.
    """
    sep = ";" if _WINDOWS else ":"
    suffix = "\\" if _WINDOWS else "/"
    target = directory.strip().removesuffix(suffix)

    parts = [p for p in os.environ.get("PATH", "").split(sep) if p]
    normalized = [p.removesuffix(suffix) for p in parts]

    if target not in normalized:
        return

    current_index = normalized.index(target)
    entry = parts.pop(current_index)
    parts.insert(index, entry)
    os.environ["PATH"] = sep.join(parts)


def list_paths(filter: Callable[[Path], bool] | None = None) -> list[Path]:
    """Return the current PATH entries as a list of Path objects.

    Pass a *filter* predicate to keep only matching entries.
    """
    sep = ";" if _WINDOWS else ":"
    paths = [Path(p) for p in os.environ.get("PATH", "").split(sep) if p]
    return [p for p in paths if filter(p)] if filter else paths


def path_len() -> int:
    """Return the number of entries in PATH."""
    sep = ";" if _WINDOWS else ":"
    return sum(1 for p in os.environ.get("PATH", "").split(sep) if p)


def in_path(directory: str) -> bool:
    """Return True if *directory* is present in PATH."""
    sep = ";" if _WINDOWS else ":"
    suffix = "\\" if _WINDOWS else "/"
    target = directory.strip().removesuffix(suffix)

    return any(
        p.removesuffix(suffix) == target
        for p in os.environ.get("PATH", "").split(sep)
        if p
    )


def clean_path() -> list[Path]:
    """Remove duplicate and non-existent directories from PATH in the current process.

    Returns the cleaned list of Path objects.
    """
    sep = ";" if _WINDOWS else ":"
    seen: set[str] = set()
    cleaned: list[str] = []

    for part in os.environ.get("PATH", "").split(sep):
        if not part:
            continue
        resolved = str(Path(part).resolve())
        if resolved in seen:
            continue
        if not Path(part).is_dir():
            continue
        seen.add(resolved)
        cleaned.append(part)

    os.environ["PATH"] = sep.join(cleaned)
    return [Path(p) for p in cleaned]


def find_executable(name: str) -> Path | None:
    """Return the first Path in PATH where *name* is an executable file, or None."""
    sep = ";" if _WINDOWS else ":"
    suffix = "\\" if _WINDOWS else "/"

    for part in os.environ.get("PATH", "").split(sep):
        if not part:
            continue
        candidate = Path(part.removesuffix(suffix)) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    return None


def find_all_executables(name: str) -> list[Path]:
    """Return all paths in PATH where *name* is an executable file (shadows included)."""
    sep = ";" if _WINDOWS else ":"
    suffix = "\\" if _WINDOWS else "/"

    results = []
    for part in os.environ.get("PATH", "").split(sep):
        if not part:
            continue
        candidate = Path(part.removesuffix(suffix)) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            results.append(candidate)

    return results


def diff_paths(before: list[Path], after: list[Path]) -> dict[str, list[Path]]:
    """Compare two PATH lists; return {"added": [...], "removed": [...]}."""
    before_set = set(before)
    after_set = set(after)
    return {
        "added": [p for p in after if p not in before_set],
        "removed": [p for p in before if p not in after_set],
    }


def duplicate_paths() -> list[Path]:
    """Return PATH entries that appear more than once (resolved duplicates)."""
    sep = ";" if _WINDOWS else ":"
    parts = [Path(p) for p in os.environ.get("PATH", "").split(sep) if p]

    seen: set[str] = set()
    duplicates: list[Path] = []

    for p in parts:
        resolved = str(p.resolve())
        if resolved in seen:
            duplicates.append(p)
        else:
            seen.add(resolved)

    return duplicates


def swap_paths(directory_a: str, directory_b: str) -> None:
    """Swap the positions of two PATH entries in the current process."""
    sep = ";" if _WINDOWS else ":"
    suffix = "\\" if _WINDOWS else "/"

    a = directory_a.strip().removesuffix(suffix)
    b = directory_b.strip().removesuffix(suffix)

    parts = [p for p in os.environ.get("PATH", "").split(sep) if p]
    normalized = [p.removesuffix(suffix) for p in parts]

    if a not in normalized or b not in normalized:
        return

    idx_a, idx_b = normalized.index(a), normalized.index(b)
    parts[idx_a], parts[idx_b] = parts[idx_b], parts[idx_a]
    os.environ["PATH"] = sep.join(parts)


def rename_path(old: str, new: str) -> None:
    """Replace *old* with *new* in PATH, preserving its position. No-op if absent."""
    sep = ";" if _WINDOWS else ":"
    suffix = "\\" if _WINDOWS else "/"

    target = old.strip().removesuffix(suffix)
    replacement = new.strip().removesuffix(suffix)

    parts = [p for p in os.environ.get("PATH", "").split(sep) if p]
    normalized = [p.removesuffix(suffix) for p in parts]

    if target not in normalized:
        return

    idx = normalized.index(target)
    parts[idx] = replacement
    os.environ["PATH"] = sep.join(parts)


def snapshot_path() -> list[str]:
    """Return the current PATH as a list of strings for later restoration."""
    sep = ";" if _WINDOWS else ":"
    return [p for p in os.environ.get("PATH", "").split(sep) if p]


def restore_path(snapshot: list[str]) -> None:
    """Restore PATH from a snapshot produced by *snapshot_path*."""
    sep = ";" if _WINDOWS else ":"
    os.environ["PATH"] = sep.join(snapshot)


def save_path_to_file(file: str | Path) -> None:
    """Write current PATH entries to *file*, one per line."""
    sep = ";" if _WINDOWS else ":"
    entries = [p for p in os.environ.get("PATH", "").split(sep) if p]
    Path(file).write_text("\n".join(entries) + "\n")


def load_path_from_file(file: str | Path) -> None:
    """Add each line in *file* as a PATH entry (appended, idempotent)."""
    for line in Path(file).read_text().splitlines():
        line = line.strip()
        if line:
            add_path(line)


class path_context:  # noqa: N801
    """Context manager that temporarily adds *directories* to PATH.

    On exit the original PATH is restored, even if an exception occurs.

    Usage::

        with path_context("/tmp/mybin", "/opt/extra/bin"):
            ...  # directories are in PATH here
        # PATH is restored here
    """

    def __init__(self, *directories: str) -> None:
        self._directories = directories
        self._snapshot: list[str] = []

    def __enter__(self):
        self._snapshot = snapshot_path()
        for directory in self._directories:
            add_path(directory)
        return self

    def __exit__(self, *_):
        restore_path(self._snapshot)
        return False


def _resolve_filter(args, parser):
    from pathreg import filters as f

    if not args.filter:
        return None

    _numeric_filters = {"depth", "min_depth", "max_depth", "newer_than", "older_than"}
    _arg_filters = _numeric_filters | {
        "contains",
        "matches",
        "startswith",
        "has_executable",
    }
    _simple_filters = {
        "exists": f.exists,
        "writable": f.writable,
        "readable": f.readable,
        "is_symlink": f.is_symlink,
        "is_real": f.is_real,
        "is_empty": f.is_empty,
        "is_nonempty": f.is_nonempty,
        "has_executables": f.has_executables,
        "is_user": f.is_user,
        "is_system": f.is_system,
        "is_venv": f.is_venv,
    }

    if args.filter not in _arg_filters:
        return _simple_filters[args.filter]

    if not args.filter_arg:
        parser.error(f"--filter {args.filter} requires --filter-arg")

    arg = float(args.filter_arg) if args.filter in _numeric_filters else args.filter_arg
    return getattr(f, args.filter)(arg)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pathreg", description="Manage PATH entries.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("remove", "Remove a directory from PATH"),
        ("check", "Check if a directory is in PATH"),
        ("find", "Find the first executable by name in PATH"),
    ):
        sub.add_parser(name, help=help_text).add_argument(
            "directory" if name != "find" else "name"
        )

    sub.add_parser("prepend", help="Add a directory to the front of PATH").add_argument(
        "directory"
    )

    add_sub = sub.add_parser("add", help="Append a directory to PATH")
    add_sub.add_argument("directory")
    add_sub.add_argument(
        "--index",
        type=int,
        default=None,
        help="Position to insert (default: append to end)",
    )

    move_sub = sub.add_parser("move", help="Move a PATH entry to a specific position")
    move_sub.add_argument("directory")
    move_sub.add_argument("index", type=int)

    list_sub = sub.add_parser("list", help="List all PATH entries")
    list_sub.add_argument(
        "--filter",
        dest="filter",
        choices=[
            "exists",
            "writable",
            "readable",
            "is_symlink",
            "is_real",
            "is_empty",
            "is_nonempty",
            "has_executables",
            "is_user",
            "is_system",
            "is_venv",
            "has_executable",
            "depth",
            "min_depth",
            "max_depth",
            "newer_than",
            "older_than",
            "contains",
            "matches",
            "startswith",
        ],
        help="Filter entries",
    )
    list_sub.add_argument("--filter-arg", dest="filter_arg", help="Argument for filter")

    sub.add_parser("count", help="Print the number of PATH entries")
    sub.add_parser("clean", help="Remove duplicates and non-existent dirs from PATH")
    sub.add_parser("duplicates", help="List entries that appear more than once")

    set_sub = sub.add_parser("set", help="Replace PATH with given directories")
    set_sub.add_argument("directories", nargs="+", metavar="directory")

    find_all_sub = sub.add_parser(
        "find-all", help="Find all executables by name in PATH"
    )
    find_all_sub.add_argument("name")

    swap_sub = sub.add_parser("swap", help="Swap positions of two PATH entries")
    swap_sub.add_argument("directory_a")
    swap_sub.add_argument("directory_b")

    rename_sub = sub.add_parser("rename", help="Replace a PATH entry in-place")
    rename_sub.add_argument("old")
    rename_sub.add_argument("new")

    save_sub = sub.add_parser("save", help="Write PATH entries to a file")
    save_sub.add_argument("file")

    load_sub = sub.add_parser("load", help="Add PATH entries from a file")
    load_sub.add_argument("file")

    return parser


def _dispatch(args, parser) -> None:
    if args.command == "list":
        for path in list_paths(_resolve_filter(args, parser)):
            print(path)
        return

    if args.command == "count":
        print(path_len())
        return

    if args.command == "clean":
        for path in clean_path():
            print(path)
        return

    if args.command == "set":
        set_path(args.directories)
        print("Path set to: " + os.pathsep.join(args.directories))
        return

    if args.command == "check":
        print("yes" if in_path(args.directory) else "no")
        return

    if args.command == "find":
        result = find_executable(args.name)
        print(result if result else "not found")
        return

    if args.command == "prepend":
        prepend_path(args.directory)
        print(f"Prepended {args.directory!r}")
        return

    if args.command == "add":
        add_path(args.directory, args.index)
        suffix = f" at index {args.index}" if args.index is not None else ""
        print(f"Added {args.directory!r}{suffix}")
        return

    if args.command == "move":
        move_path(args.directory, args.index)
        print(f"Moved {args.directory!r} to index {args.index}")
        return

    if args.command == "find-all":
        results = find_all_executables(args.name)
        for path in results:
            print(path)
        if not results:
            print("not found")
        return

    if args.command == "duplicates":
        for path in duplicate_paths():
            print(path)
        return

    if args.command == "swap":
        swap_paths(args.directory_a, args.directory_b)
        print(f"Swapped {args.directory_a!r} and {args.directory_b!r}")
        return

    if args.command == "rename":
        rename_path(args.old, args.new)
        print(f"Renamed {args.old!r} to {args.new!r}")
        return

    if args.command == "save":
        save_path_to_file(args.file)
        print(f"Saved PATH to {args.file!r}")
        return

    if args.command == "load":
        load_path_from_file(args.file)
        print(f"Loaded PATH entries from {args.file!r}")
        return

    remove_path(args.directory)
    print(f"Removed {args.directory!r}")


def main():
    parser = _build_parser()
    _dispatch(parser.parse_args(), parser)


if __name__ == "__main__":
    main()
