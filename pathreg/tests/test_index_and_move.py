import os
from unittest.mock import patch

from pathreg import _add_path_unix, _entry, main, move_path


class TestAddPathUnixIndex:
    def test_default_appends_to_environ(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            _add_path_unix("/new")
            assert os.environ["PATH"].endswith(":/new")

    def test_default_appends_to_profile(self, sh_profile):
        sh_profile.write_text(_entry("/a") + _entry("/b"))
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            _add_path_unix("/new")
        content = sh_profile.read_text()
        assert content.index(_entry("/new")) > content.index(_entry("/b"))

    def test_index_zero_inserts_at_front_in_profile(self, sh_profile):
        sh_profile.write_text(_entry("/a") + _entry("/b"))
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            _add_path_unix("/new", index=0)
        content = sh_profile.read_text()
        assert content.index(_entry("/new")) < content.index(_entry("/a"))

    def test_index_zero_prepends_in_environ(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            _add_path_unix("/new", index=0)
            assert os.environ["PATH"].startswith("/new:")

    def test_index_one_inserts_after_first(self, sh_profile):
        sh_profile.write_text(_entry("/a") + _entry("/b"))
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            _add_path_unix("/new", index=1)
        content = sh_profile.read_text()
        assert content.index(_entry("/a")) < content.index(_entry("/new"))
        assert content.index(_entry("/new")) < content.index(_entry("/b"))

    def test_index_places_entry_in_environ(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            _add_path_unix("/new", index=2)
            parts = os.environ["PATH"].split(":")
            assert parts[2] == "/new"

    def test_index_beyond_end_appends(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/a"}):
            _add_path_unix("/new", index=99)
            assert os.environ["PATH"].endswith(":/new")

    def test_negative_index_inserts_from_end(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            _add_path_unix("/new", index=-1)
            parts = os.environ["PATH"].split(":")
            assert parts[-2] == "/new"

    def test_idempotent_with_index(self, sh_profile):
        sh_profile.write_text(_entry("/new"))
        with patch.dict(os.environ, {"PATH": "/new:/a"}):
            _add_path_unix("/new", index=0)
        assert sh_profile.read_text().count(_entry("/new")) == 1

    def test_preserves_non_path_lines_in_profile(self, sh_profile):
        sh_profile.write_text("export EDITOR=vim\n")
        with patch.dict(os.environ, {"PATH": "/a"}):
            _add_path_unix("/new", index=0)
        assert "export EDITOR=vim\n" in sh_profile.read_text()


class TestMovePath:
    def test_moves_entry_to_front(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            move_path("/c", 0)
            assert os.environ["PATH"] == "/c:/a:/b"

    def test_moves_entry_to_end(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            move_path("/a", 2)
            assert os.environ["PATH"] == "/b:/c:/a"

    def test_moves_entry_to_middle(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            move_path("/c", 1)
            assert os.environ["PATH"] == "/a:/c:/b"

    def test_no_op_when_not_in_path(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            move_path("/missing", 0)
            assert os.environ["PATH"] == "/a:/b"

    def test_strips_trailing_slash(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            move_path("/c/", 0)
            assert os.environ["PATH"] == "/c:/a:/b"

    def test_index_beyond_end_appends(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            move_path("/a", 99)
            assert os.environ["PATH"] == "/b:/c:/a"


class TestMainAddIndex:
    def test_add_with_index_flag(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "add", "--index", "1", "/new"]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_print.assert_called_with("Added '/new' at index 1")

    def test_add_default_appends(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "add", "/new"]),
            patch.dict(os.environ, {"PATH": "/a"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            assert os.environ["PATH"].endswith(":/new")
        mock_print.assert_called_with("Added '/new'")


class TestMainMove:
    def test_move_command(self):
        with (
            patch("sys.argv", ["pathreg", "move", "/b", "0"]),
            patch.dict(os.environ, {"PATH": "/a:/b:/c"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            assert os.environ["PATH"] == "/b:/a:/c"
        mock_print.assert_called_with("Moved '/b' to index 0")

    def test_move_no_op_prints_message(self):
        with (
            patch("sys.argv", ["pathreg", "move", "/missing", "0"]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            assert os.environ["PATH"] == "/a:/b"
        mock_print.assert_called_with("Moved '/missing' to index 0")
