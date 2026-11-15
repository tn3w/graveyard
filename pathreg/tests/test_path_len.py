import os
from unittest.mock import patch

from pathreg import main, path_len


class TestPathLen:
    def test_counts_entries(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            assert path_len() == 3

    def test_empty_path(self):
        with patch.dict(os.environ, {}, clear=True):
            assert path_len() == 0

    def test_single_entry(self):
        with patch.dict(os.environ, {"PATH": "/a"}):
            assert path_len() == 1

    def test_ignores_empty_segments(self):
        with patch.dict(os.environ, {"PATH": "/a::/b"}):
            assert path_len() == 2

    def test_cli_count(self):
        with (
            patch("sys.argv", ["pathreg", "count"]),
            patch.dict(os.environ, {"PATH": "/a:/b:/c"}),
            patch("builtins.print") as mock_print,
        ):
            main()
        mock_print.assert_called_once_with(3)
