import os
import sys
from unittest.mock import patch

import pytest

from pathreg import _entry, main


class TestMain:
    def test_add_prints_added(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "add", "/some/dir"]),
            patch.dict(os.environ, {"PATH": "/existing"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            mock_print.assert_called_once_with("Added '/some/dir'")

    def test_remove_prints_removed(self, sh_profile):
        sh_profile.write_text(_entry("/some/dir"))
        with (
            patch("sys.argv", ["pathreg", "remove", "/some/dir"]),
            patch.dict(os.environ, {"PATH": "/some/dir:/existing"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            mock_print.assert_called_once_with("Removed '/some/dir'")

    def test_no_command_exits(self):
        with patch("sys.argv", ["pathreg"]):
            with pytest.raises(SystemExit):
                main()

    def test_unknown_command_exits(self):
        with patch("sys.argv", ["pathreg", "unknown"]):
            with pytest.raises(SystemExit):
                main()

    def test_add_without_directory_exits(self):
        with patch("sys.argv", ["pathreg", "add"]):
            with pytest.raises(SystemExit):
                main()

    def test_remove_without_directory_exits(self):
        with patch("sys.argv", ["pathreg", "remove"]):
            with pytest.raises(SystemExit):
                main()

    def test_add_modifies_profile(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "add", "/cli/dir"]),
            patch.dict(os.environ, {"PATH": "/existing"}),
            patch("builtins.print"),
        ):
            main()
        assert _entry("/cli/dir") in sh_profile.read_text()

    def test_remove_modifies_profile(self, sh_profile):
        sh_profile.write_text(_entry("/cli/dir"))
        with (
            patch("sys.argv", ["pathreg", "remove", "/cli/dir"]),
            patch.dict(os.environ, {"PATH": "/cli/dir:/existing"}),
            patch("builtins.print"),
        ):
            main()
        assert _entry("/cli/dir") not in sh_profile.read_text()

    def test_help_flag_exits_with_zero(self):
        with patch("sys.argv", ["pathreg", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_add_output_contains_quoted_directory(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "add", "/quoted/dir"]),
            patch.dict(os.environ, {"PATH": "/existing"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert "'/quoted/dir'" in mock_print.call_args[0][0]

    def test_remove_output_contains_quoted_directory(self, sh_profile):
        sh_profile.write_text(_entry("/quoted/dir"))
        with (
            patch("sys.argv", ["pathreg", "remove", "/quoted/dir"]),
            patch.dict(os.environ, {"PATH": "/quoted/dir:/existing"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert "'/quoted/dir'" in mock_print.call_args[0][0]

    def test_add_prints_original_arg_with_trailing_slash(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "add", "/some/dir/"]),
            patch.dict(os.environ, {"PATH": "/existing"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert "'/some/dir/'" in mock_print.call_args[0][0]


class TestDunderMain:
    def test_module_main_help_exits_zero(self):
        import inspect

        import pathreg as _mod

        source_path = inspect.getfile(_mod)
        import subprocess

        completed = subprocess.run(
            [sys.executable, source_path, "--help"],
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0
        assert "add" in completed.stdout

    def test_dunder_main_guard_calls_main(self):
        import inspect
        import runpy

        import pathreg

        source_path = inspect.getfile(pathreg)
        with (patch("sys.argv", ["pathreg", "--help"]),):
            with pytest.raises(SystemExit) as exc_info:
                runpy.run_path(source_path, run_name="__main__")
        assert exc_info.value.code == 0


class TestCheckCommand:
    def test_prints_yes_when_present(self):
        with (
            patch("sys.argv", ["pathreg", "check", "/some/dir"]),
            patch.dict(os.environ, {"PATH": "/some/dir:/usr/bin"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            mock_print.assert_called_once_with("yes")

    def test_prints_no_when_absent(self):
        with (
            patch("sys.argv", ["pathreg", "check", "/some/dir"]),
            patch.dict(os.environ, {"PATH": "/usr/bin"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            mock_print.assert_called_once_with("no")

    def test_check_without_directory_exits(self):
        with patch("sys.argv", ["pathreg", "check"]):
            with pytest.raises(SystemExit):
                main()


class TestNewCommands:
    def test_find_all_prints_matches(self, tmp_path):
        import stat

        exe = tmp_path / "mytool"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        with (
            patch("sys.argv", ["pathreg", "find-all", "mytool"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_print.assert_called_once_with(tmp_path / "mytool")

    def test_find_all_prints_not_found(self, tmp_path):
        with (
            patch("sys.argv", ["pathreg", "find-all", "no_such_bin"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_print.assert_called_once_with("not found")

    def test_duplicates_prints_duplicates(self):
        with (
            patch("sys.argv", ["pathreg", "duplicates"]),
            patch.dict(os.environ, {"PATH": "/a:/b:/a"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        from pathlib import Path

        mock_print.assert_called_once_with(Path("/a"))

    def test_swap_prints_confirmation(self):
        with (
            patch("sys.argv", ["pathreg", "swap", "/a", "/b"]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_print.assert_called_once_with("Swapped '/a' and '/b'")

    def test_rename_prints_confirmation(self):
        with (
            patch("sys.argv", ["pathreg", "rename", "/a", "/z"]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_print.assert_called_once_with("Renamed '/a' to '/z'")

    def test_save_prints_confirmation(self, tmp_path):
        file = str(tmp_path / "paths.txt")
        with (
            patch("sys.argv", ["pathreg", "save", file]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert f"Saved PATH to {file!r}" == mock_print.call_args[0][0]

    def test_load_prints_confirmation(self, tmp_path, sh_profile):
        file = tmp_path / "paths.txt"
        file.write_text("/a\n")
        with (
            patch("sys.argv", ["pathreg", "load", str(file)]),
            patch.dict(os.environ, {"PATH": ""}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert f"Loaded PATH entries from {str(file)!r}" == mock_print.call_args[0][0]


class TestAliases:
    def test_add_path_is_unix_on_non_windows(self):
        if sys.platform not in ("win32", "cygwin"):
            from pathreg import _add_path_unix, add_path

            assert add_path is _add_path_unix

    def test_remove_path_is_unix_on_non_windows(self):
        if sys.platform not in ("win32", "cygwin"):
            from pathreg import _remove_path_unix, remove_path

            assert remove_path is _remove_path_unix
