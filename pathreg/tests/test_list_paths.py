import os
from pathlib import Path
from unittest.mock import patch

from pathreg import list_paths, main


class TestListPaths:
    def test_returns_list_of_paths(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin:/usr/local/bin"}):
            result = list_paths()
        assert result == [Path("/usr/bin"), Path("/usr/local/bin")]

    def test_single_entry(self):
        with patch.dict(os.environ, {"PATH": "/only/one"}):
            assert list_paths() == [Path("/only/one")]

    def test_empty_path_returns_empty_list(self):
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        with patch.dict(os.environ, env, clear=True):
            assert list_paths() == []

    def test_skips_empty_segments(self):
        with patch.dict(os.environ, {"PATH": "/a::/b"}):
            assert list_paths() == [Path("/a"), Path("/b")]

    def test_returns_path_objects(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin"}):
            result = list_paths()
        assert all(isinstance(p, Path) for p in result)

    def test_preserves_order(self):
        dirs = ["/z/last", "/a/first", "/m/middle"]
        with patch.dict(os.environ, {"PATH": ":".join(dirs)}):
            result = list_paths()
        assert result == [Path(d) for d in dirs]


class TestMainList:
    def test_list_prints_each_path(self, capsys):
        with (
            patch("sys.argv", ["pathreg", "list"]),
            patch.dict(os.environ, {"PATH": "/usr/bin:/usr/local/bin"}),
        ):
            main()
        out = capsys.readouterr().out.splitlines()
        assert out == ["/usr/bin", "/usr/local/bin"]

    def test_list_empty_path_prints_nothing(self, capsys):
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        with (
            patch("sys.argv", ["pathreg", "list"]),
            patch.dict(os.environ, env, clear=True),
        ):
            main()
        assert capsys.readouterr().out == ""
