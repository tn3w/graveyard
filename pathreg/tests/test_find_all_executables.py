import os
import stat
from pathlib import Path
from unittest.mock import patch

from pathreg import find_all_executables


def _make_exe(directory: Path, name: str) -> Path:
    exe = directory / name
    exe.write_text("#!/bin/sh\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return exe


class TestFindAllExecutables:
    def test_returns_all_matches(self, tmp_path):
        dir1 = tmp_path / "bin1"
        dir2 = tmp_path / "bin2"
        dir1.mkdir()
        dir2.mkdir()
        _make_exe(dir1, "python")
        _make_exe(dir2, "python")

        with patch.dict(os.environ, {"PATH": f"{dir1}:{dir2}"}):
            results = find_all_executables("python")

        assert results == [dir1 / "python", dir2 / "python"]

    def test_returns_empty_when_not_found(self, tmp_path):
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_all_executables("nonexistent_xyz") == []

    def test_skips_non_executable(self, tmp_path):
        (tmp_path / "tool").write_text("data")
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_all_executables("tool") == []

    def test_returns_single_match(self, tmp_path):
        _make_exe(tmp_path, "mytool")
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_all_executables("mytool") == [tmp_path / "mytool"]

    def test_skips_empty_path_components(self, tmp_path):
        _make_exe(tmp_path, "mytool")
        with patch.dict(os.environ, {"PATH": f":{tmp_path}:"}):
            results = find_all_executables("mytool")
        assert results == [tmp_path / "mytool"]
