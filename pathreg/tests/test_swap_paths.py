import os
from unittest.mock import patch

from pathreg import swap_paths


class TestSwapPaths:
    def test_swaps_two_entries(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            swap_paths("/a", "/c")
            assert os.environ["PATH"] == "/c:/b:/a"

    def test_noop_when_first_absent(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            swap_paths("/x", "/a")
            assert os.environ["PATH"] == "/a:/b"

    def test_noop_when_second_absent(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            swap_paths("/a", "/x")
            assert os.environ["PATH"] == "/a:/b"

    def test_adjacent_swap(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            swap_paths("/a", "/b")
            assert os.environ["PATH"] == "/b:/a"

    def test_noop_when_both_absent(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            swap_paths("/x", "/y")
            assert os.environ["PATH"] == "/a:/b"
