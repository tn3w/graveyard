# pathreg

Persistently add or remove directories from `PATH` on Windows, Linux, and macOS.

## Installation

```sh
pip install pathreg
```

## CLI Usage

```sh
pathreg add /some/directory             # append (default)
pathreg add --index 0 /some/directory   # insert at position 0
pathreg prepend /some/directory         # insert at front
pathreg remove /some/directory
pathreg move /some/directory 0          # move existing entry to position 0
pathreg set /a /b /c                    # replace PATH with given directories
pathreg list
pathreg list --filter exists
pathreg list --filter writable
pathreg list --filter readable
pathreg list --filter is_symlink
pathreg list --filter is_real
pathreg list --filter is_empty
pathreg list --filter is_nonempty
pathreg list --filter has_executables
pathreg list --filter is_user
pathreg list --filter is_system
pathreg list --filter is_venv
pathreg list --filter has_executable --filter-arg python
pathreg list --filter depth      --filter-arg 3
pathreg list --filter min_depth  --filter-arg 2
pathreg list --filter max_depth  --filter-arg 4
pathreg list --filter newer_than --filter-arg 7     # days
pathreg list --filter older_than --filter-arg 30
pathreg list --filter contains   --filter-arg usr
pathreg list --filter matches    --filter-arg "^/usr"
pathreg list --filter startswith --filter-arg /usr
pathreg count                           # prints number of PATH entries
pathreg check /some/directory           # prints "yes" or "no"
pathreg find python                     # prints full path or "not found"
pathreg find-all python                 # prints all matches (shadows included), or "not found"
pathreg clean                           # removes duplicates and non-existent entries
pathreg duplicates                      # list entries that appear more than once
pathreg swap /a /b                      # swap positions of two entries
pathreg rename /old /new                # replace an entry in-place, keeping its position
pathreg save /path/to/file.txt          # write current PATH entries to a file, one per line
pathreg load /path/to/file.txt          # add entries from a file
```

## Python API

```python
from pathreg import (
    add_path, prepend_path, remove_path, move_path, set_path,
    list_paths, path_len, in_path, find_executable, find_all_executables,
    clean_path, diff_paths, duplicate_paths, swap_paths, rename_path,
    snapshot_path, restore_path, save_path_to_file, load_path_from_file,
    path_context,
)
from pathreg import filters

add_path("/some/directory")          # append (default); idempotent
add_path("/some/directory", index=0) # insert at position 0; idempotent
prepend_path("/some/directory")      # insert at front; idempotent
remove_path("/some/directory")       # no-op if not found
move_path("/some/directory", 0)      # move existing entry to position 0; no-op if absent
set_path(["/a", "/b", "/c"])         # replace PATH entirely
list_paths()                         # returns list[Path] of current PATH entries
list_paths(filters.exists)           # pass any callable(Path) -> bool as filter
list_paths(filters.contains("usr"))  # factory filters return a predicate
path_len()                           # returns number of PATH entries (faster than len(list_paths()))
in_path("/some/directory")           # returns True if directory is in PATH
find_executable("python")            # returns Path to first match, or None
find_all_executables("python")       # returns list[Path] of all matches (useful for spotting shadows)
clean_path()                         # removes duplicates and non-existent dirs, returns cleaned list[Path]
diff_paths(before, after)            # returns {"added": [...], "removed": [...]} comparing two PATH lists
duplicate_paths()                    # returns entries that appear more than once (does not modify PATH)
swap_paths("/a", "/b")               # swap positions of two entries in the current process
rename_path("/old", "/new")          # replace an entry in-place, keeping its position
snapshot_path()                      # returns current PATH as list[str] for later restoration
restore_path(snapshot)               # restores PATH from a snapshot_path() result
save_path_to_file("/path/file.txt")  # writes current PATH entries to a file, one per line
load_path_from_file("/path/file.txt") # adds entries from a file (idempotent)

with path_context("/tmp/mybin", "/opt/extra"):
    ...  # directories are in PATH here; PATH restored on exit (even on exception)
```

`add_path`, `remove_path`, `move_path`, and `set_path` modify the shell profile **and** the current process's `PATH` immediately (`move_path` only updates the current process).

## Behavior

- Paths are normalized: trailing separators stripped, slashes converted per platform.
- `add_path` is idempotent, does nothing if the entry already exists. The optional `index` parameter controls insertion position (default `None` = append to end); supports negative indices.
- `move_path` moves an existing entry to the given index in the current process PATH only; no-op if absent.
- `remove_path` is a no-op if the entry is absent or the profile file does not exist.
- `list_paths` reflects the current process `PATH`; it does not read the profile file. An optional `filter` predicate (`Callable[[Path], bool]`) narrows the results.
- `pathreg.filters` provides ready-made predicates:
    - **Plain**: `exists`, `writable`, `readable`, `is_symlink`, `is_real`, `is_empty`, `is_nonempty`, `has_executables`, `is_user`, `is_system`, `is_venv`
    - **Factories** (return a predicate): `contains(s)`, `matches(pattern)`, `startswith(prefix)`, `has_executable(name)`, `depth(n)`, `min_depth(n)`, `max_depth(n)`, `newer_than(days)`, `older_than(days)`
    - **Combinators**: `not_(pred)`, `all_(*preds)`, `any_(*preds)`
- `in_path` normalizes trailing separators before comparing, matching `add_path` behaviour.
- `find_executable` walks PATH entries in order and returns the first regular file that is executable, or `None`.
- `clean_path` removes non-existent directories and duplicates (resolved via symlinks) from the current process PATH in-place, and returns the cleaned list.
- `find_all_executables` walks all PATH entries and returns every match, not just the first — useful for detecting shadowed binaries.
- `diff_paths(before, after)` compares two `list[Path]` values and returns `{"added": [...], "removed": [...]}` — useful for debugging shell startup changes.
- `duplicate_paths` returns entries that appear more than once (resolved via symlinks) without modifying PATH.
- `swap_paths(a, b)` swaps the positions of two entries in the current process PATH; no-op if either is absent.
- `rename_path(old, new)` replaces _old_ with _new_ at the same position; no-op if absent.
- `snapshot_path` / `restore_path` save and restore PATH as a plain `list[str]` — useful in scripts and tests.
- `save_path_to_file` / `load_path_from_file` write/read PATH entries one per line.
- `path_context(*directories)` is a context manager that adds directories for the duration of a `with` block then restores PATH — works correctly even when exceptions are raised.

## Platform support

| Platform | Persistence target                                                                 |
| -------- | ---------------------------------------------------------------------------------- |
| Windows  | `HKCU\Environment` via `winreg`; broadcasts `WM_SETTINGCHANGE` to notify the shell |
| bash     | `~/.bash_profile` (falls back to `~/.profile` if it exists)                        |
| zsh      | `~/.zshenv`                                                                        |
| sh       | `~/.profile`                                                                       |

The active shell is detected from the `SHELL` environment variable.

No third-party dependencies required.
