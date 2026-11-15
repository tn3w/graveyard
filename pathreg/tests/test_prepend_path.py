import os
from unittest.mock import patch

from pathreg import _entry, main, prepend_path


class TestPrependPath:
    def test_inserts_at_front_of_environ(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            prepend_path("/new")
            assert os.environ["PATH"].startswith("/new:")

    def test_inserts_at_front_of_profile(self, sh_profile):
        sh_profile.write_text(_entry("/a") + _entry("/b"))
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            prepend_path("/new")
        content = sh_profile.read_text()
        assert content.index(_entry("/new")) < content.index(_entry("/a"))

    def test_idempotent(self, sh_profile):
        sh_profile.write_text(_entry("/new"))
        with patch.dict(os.environ, {"PATH": "/new:/a"}):
            prepend_path("/new")
        assert sh_profile.read_text().count(_entry("/new")) == 1

    def test_cli_prepend(self, sh_profile):
        with (
            patch("sys.argv", ["pathreg", "prepend", "/new"]),
            patch.dict(os.environ, {"PATH": "/a:/b"}),
            patch("builtins.print") as mock_print,
        ):
            main()
            assert os.environ["PATH"].startswith("/new:")
        mock_print.assert_called_once_with("Prepended '/new'")
