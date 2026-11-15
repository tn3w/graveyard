import os
from pathlib import Path
from unittest.mock import patch

from pathreg import duplicate_paths


class TestDuplicatePaths:
    def test_no_duplicates(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            assert duplicate_paths() == []

    def test_detects_duplicate(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/a"}):
            assert Path("/a") in duplicate_paths()

    def test_empty_path(self):
        with patch.dict(os.environ, {"PATH": ""}):
            assert duplicate_paths() == []

    def test_does_not_modify_env(self):
        with patch.dict(os.environ, {"PATH": "/x:/y:/x"}):
            duplicate_paths()
            assert os.environ["PATH"] == "/x:/y:/x"

    def test_returns_second_occurrence(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/a"}):
            result = duplicate_paths()
        assert result == [Path("/a")]
