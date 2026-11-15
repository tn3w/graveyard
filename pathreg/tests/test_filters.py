import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pathreg import filters, list_paths, main


class TestExistenceFilters:
    def test_exists_true(self, tmp_path):
        assert filters.exists(tmp_path) is True

    def test_exists_false(self, tmp_path):
        assert filters.exists(tmp_path / "missing") is False

    def test_writable_true(self, tmp_path):
        assert filters.writable(tmp_path) is True

    def test_writable_false_missing(self, tmp_path):
        assert filters.writable(tmp_path / "missing") is False

    def test_readable_true(self, tmp_path):
        assert filters.readable(tmp_path) is True

    def test_readable_false_missing(self, tmp_path):
        assert filters.readable(tmp_path / "missing") is False

    def test_is_symlink_true(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)
        assert filters.is_symlink(link) is True

    def test_is_symlink_false(self, tmp_path):
        assert filters.is_symlink(tmp_path) is False

    def test_is_real_true(self, tmp_path):
        assert filters.is_real(tmp_path) is True

    def test_is_real_false_for_symlink(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)
        assert filters.is_real(link) is False

    def test_is_real_false_missing(self, tmp_path):
        assert filters.is_real(tmp_path / "missing") is False


class TestContentFilters:
    def test_is_empty_true(self, tmp_path):
        assert filters.is_empty(tmp_path) is True

    def test_is_empty_false(self, tmp_path):
        (tmp_path / "file").touch()
        assert filters.is_empty(tmp_path) is False

    def test_is_empty_missing(self, tmp_path):
        assert filters.is_empty(tmp_path / "missing") is False

    def test_is_nonempty_true(self, tmp_path):
        (tmp_path / "file").touch()
        assert filters.is_nonempty(tmp_path) is True

    def test_is_nonempty_false(self, tmp_path):
        assert filters.is_nonempty(tmp_path) is False

    def test_has_executables_true(self, tmp_path):
        exe = tmp_path / "prog"
        exe.touch()
        exe.chmod(0o755)
        assert filters.has_executables(tmp_path) is True

    def test_has_executables_false(self, tmp_path):
        (tmp_path / "file.txt").touch()
        assert filters.has_executables(tmp_path) is False

    def test_has_executables_missing(self, tmp_path):
        assert filters.has_executables(tmp_path / "missing") is False

    def test_has_executable_true(self, tmp_path):
        exe = tmp_path / "python"
        exe.touch()
        exe.chmod(0o755)
        assert filters.has_executable("python")(tmp_path) is True

    def test_has_executable_false(self, tmp_path):
        assert filters.has_executable("python")(tmp_path) is False


class TestPathStructureFilters:
    def test_depth_exact(self):
        assert filters.depth(4)(Path("/a/b/c")) is True
        assert filters.depth(4)(Path("/a/b")) is False

    def test_min_depth(self):
        assert filters.min_depth(3)(Path("/a/b")) is True
        assert filters.min_depth(3)(Path("/a")) is False

    def test_max_depth(self):
        assert filters.max_depth(3)(Path("/a/b")) is True
        assert filters.max_depth(3)(Path("/a/b/c")) is False

    def test_startswith(self):
        assert filters.startswith("/usr")(Path("/usr/bin")) is True
        assert filters.startswith("/usr")(Path("/opt/bin")) is False

    def test_contains(self):
        assert filters.contains("usr")(Path("/usr/bin")) is True
        assert filters.contains("usr")(Path("/opt/bin")) is False

    def test_matches(self):
        assert filters.matches(r"^/usr")(Path("/usr/bin")) is True
        assert filters.matches(r"^/usr")(Path("/opt/bin")) is False


class TestLocationFilters:
    def test_is_user_true(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        sub = tmp_path / "bin"
        sub.mkdir()
        assert filters.is_user(sub) is True

    def test_is_user_false(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        assert filters.is_user(Path("/usr/bin")) is False

    def test_is_system_true(self):
        assert filters.is_system(Path("/usr/bin")) is True
        assert filters.is_system(Path("/bin")) is True
        assert filters.is_system(Path("/opt/local")) is True

    def test_is_system_false(self):
        assert filters.is_system(Path("/home/user/bin")) is False

    def test_is_venv_true(self, tmp_path):
        (tmp_path / "pyvenv.cfg").touch()
        sub = tmp_path / "bin"
        sub.mkdir()
        assert filters.is_venv(sub) is True

    def test_is_venv_false(self, tmp_path):
        assert filters.is_venv(tmp_path) is False


class TestTimeFilters:
    def test_newer_than_true(self, tmp_path):
        assert filters.newer_than(1)(tmp_path) is True

    def test_newer_than_false(self, tmp_path):
        assert filters.newer_than(0)(tmp_path) is False

    def test_newer_than_missing(self, tmp_path):
        assert filters.newer_than(1)(tmp_path / "missing") is False

    def test_older_than_true(self, tmp_path):
        assert filters.older_than(999999)(tmp_path) is False

    def test_older_than_missing(self, tmp_path):
        assert filters.older_than(1)(tmp_path / "missing") is False


class TestCombinators:
    def test_not_inverts(self):
        assert filters.not_(filters.is_system)(Path("/usr/bin")) is False
        assert filters.not_(filters.is_system)(Path("/home/user/bin")) is True

    def test_all_both_true(self):
        f = filters.all_(filters.contains("usr"), filters.startswith("/usr"))
        assert f(Path("/usr/bin")) is True

    def test_all_one_false(self):
        f = filters.all_(filters.contains("usr"), filters.startswith("/opt"))
        assert f(Path("/usr/bin")) is False

    def test_any_one_true(self):
        f = filters.any_(filters.contains("usr"), filters.startswith("/opt"))
        assert f(Path("/usr/bin")) is True

    def test_any_none_true(self):
        f = filters.any_(filters.contains("xyz"), filters.startswith("/zzz"))
        assert f(Path("/usr/bin")) is False


class TestListPathsFilter:
    def test_no_filter_returns_all(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            assert len(list_paths()) == 3

    def test_filter_applied(self, tmp_path):
        with patch.dict(os.environ, {"PATH": f"{tmp_path}:/nonexistent"}):
            result = list_paths(filters.exists)
        assert result == [tmp_path]

    def test_filter_contains(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin:/opt/bin:/usr/local/bin"}):
            result = list_paths(filters.contains("usr"))
        assert len(result) == 2


class TestCliListFilter:
    def test_list_no_filter(self):
        with (
            patch("sys.argv", ["pathreg", "list"]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 2

    def test_list_filter_exists(self, tmp_path):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "exists"]),
            patch.dict(os.environ, {"PATH": f"{tmp_path}:/nonexistent"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_writable(self, tmp_path):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "writable"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_readable(self, tmp_path):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "readable"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_is_symlink(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "is_symlink"]),
            patch.dict(os.environ, {"PATH": str(link)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_is_real(self, tmp_path):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "is_real"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_is_empty(self, tmp_path):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "is_empty"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_is_nonempty(self, tmp_path):
        (tmp_path / "f").touch()
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "is_nonempty"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_has_executables(self, tmp_path):
        exe = tmp_path / "prog"
        exe.touch()
        exe.chmod(0o755)
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "has_executables"]),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_is_system(self):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "is_system"]),
            patch.dict(os.environ, {"PATH": "/usr/bin:/home/user/bin"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_is_venv(self, tmp_path):
        (tmp_path / "pyvenv.cfg").touch()
        sub = tmp_path / "bin"
        sub.mkdir()
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "is_venv"]),
            patch.dict(os.environ, {"PATH": str(sub)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_has_executable(self, tmp_path):
        exe = tmp_path / "python"
        exe.touch()
        exe.chmod(0o755)
        with (
            patch(
                "sys.argv",
                [
                    "pathreg",
                    "list",
                    "--filter",
                    "has_executable",
                    "--filter-arg",
                    "python",
                ],
            ),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_depth(self):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "depth", "--filter-arg", "4"],
            ),
            patch.dict(os.environ, {"PATH": "/a/b/c:/a/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_min_depth(self):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "min_depth", "--filter-arg", "4"],
            ),
            patch.dict(os.environ, {"PATH": "/a/b/c:/a/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_max_depth(self):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "max_depth", "--filter-arg", "3"],
            ),
            patch.dict(os.environ, {"PATH": "/a/b/c:/a/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_newer_than(self, tmp_path):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "newer_than", "--filter-arg", "1"],
            ),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_older_than(self, tmp_path):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "older_than", "--filter-arg", "999999"],
            ),
            patch.dict(os.environ, {"PATH": str(tmp_path)}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 0

    def test_list_filter_contains(self):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "contains", "--filter-arg", "usr"],
            ),
            patch.dict(os.environ, {"PATH": "/usr/bin:/opt/bin"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_matches(self):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "matches", "--filter-arg", r"^/usr"],
            ),
            patch.dict(os.environ, {"PATH": "/usr/bin:/opt/bin:/usr/local"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 2

    def test_list_filter_startswith(self):
        with (
            patch(
                "sys.argv",
                ["pathreg", "list", "--filter", "startswith", "--filter-arg", "/usr"],
            ),
            patch.dict(os.environ, {"PATH": "/usr/bin:/opt/bin"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        assert mock_print.call_count == 1

    def test_list_filter_arg_required_error(self):
        with (
            patch("sys.argv", ["pathreg", "list", "--filter", "contains"]),
            patch.dict(os.environ, {"PATH": "/a"}),
            pytest.raises(SystemExit),
        ):
            main()
