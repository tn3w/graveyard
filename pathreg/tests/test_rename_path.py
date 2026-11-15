import os
from unittest.mock import patch

from pathreg import rename_path


class TestRenamePath:
    def test_renames_in_place(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            rename_path("/b", "/new")
            assert os.environ["PATH"] == "/a:/new:/c"

    def test_noop_when_absent(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            rename_path("/x", "/y")
            assert os.environ["PATH"] == "/a:/b"

    def test_position_preserved_at_front(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            rename_path("/a", "/z")
            assert os.environ["PATH"].startswith("/z:")

    def test_position_preserved_at_end(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            rename_path("/c", "/z")
            assert os.environ["PATH"].endswith(":/z")
