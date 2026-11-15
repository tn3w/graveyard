import os
from unittest.mock import patch

from pathreg import in_path


class TestInPath:
    def test_present(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin:/some/dir"}):
            assert in_path("/some/dir") is True

    def test_absent(self):
        with patch.dict(os.environ, {"PATH": "/usr/bin:/other/dir"}):
            assert in_path("/some/dir") is False

    def test_trailing_slash_normalized(self):
        with patch.dict(os.environ, {"PATH": "/some/dir:/usr/bin"}):
            assert in_path("/some/dir/") is True

    def test_empty_path(self):
        with patch.dict(os.environ, {"PATH": ""}):
            assert in_path("/some/dir") is False

    def test_exact_match_only(self):
        with patch.dict(os.environ, {"PATH": "/some/dir/extra"}):
            assert in_path("/some/dir") is False

    def test_single_entry(self):
        with patch.dict(os.environ, {"PATH": "/some/dir"}):
            assert in_path("/some/dir") is True
