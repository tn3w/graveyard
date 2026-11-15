import os
import stat
import sys
from unittest.mock import patch

from pathreg import find_executable, main


def make_executable(path):
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class TestFindExecutable:
    def test_finds_executable_in_path(self, tmp_path):
        exe = tmp_path / "mytool"
        make_executable(exe)
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_executable("mytool") == exe

    def test_returns_none_when_not_found(self, tmp_path):
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_executable("nonexistent") is None

    def test_returns_first_match(self, tmp_path):
        first = tmp_path / "a"
        second = tmp_path / "b"
        first.mkdir()
        second.mkdir()
        exe_a = first / "mytool"
        exe_b = second / "mytool"
        make_executable(exe_a)
        make_executable(exe_b)
        with patch.dict(os.environ, {"PATH": f"{first}:{second}"}):
            assert find_executable("mytool") == exe_a

    def test_skips_non_executable_file(self, tmp_path):
        non_exe = tmp_path / "mytool"
        non_exe.write_text("not executable")
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_executable("mytool") is None

    def test_skips_directory_with_same_name(self, tmp_path):
        (tmp_path / "mytool").mkdir()
        with patch.dict(os.environ, {"PATH": str(tmp_path)}):
            assert find_executable("mytool") is None

    def test_handles_trailing_separator_in_path_entry(self, tmp_path):
        exe = tmp_path / "mytool"
        make_executable(exe)
        with patch.dict(os.environ, {"PATH": str(tmp_path) + "/"}):
            assert find_executable("mytool") == exe

    def test_handles_empty_path_segments(self, tmp_path):
        exe = tmp_path / "mytool"
        make_executable(exe)
        with patch.dict(os.environ, {"PATH": f":{tmp_path}:"}):
            assert find_executable("mytool") == exe

    def test_empty_path_returns_none(self):
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        with patch.dict(os.environ, env, clear=True):
            assert find_executable("anything") is None

    def test_cli_find_found(self, tmp_path, capsys):
        exe = tmp_path / "mytool"
        make_executable(exe)
        with (
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch.object(sys, "argv", ["pathreg", "find", "mytool"]),
        ):
            main()
        assert str(exe) in capsys.readouterr().out

    def test_cli_find_not_found(self, tmp_path, capsys):
        with (
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch.object(sys, "argv", ["pathreg", "find", "missing"]),
        ):
            main()
        assert "not found" in capsys.readouterr().out
