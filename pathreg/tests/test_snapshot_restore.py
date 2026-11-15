import os
from unittest.mock import patch

from pathreg import restore_path, snapshot_path


class TestSnapshotRestore:
    def test_round_trip(self):
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            snap = snapshot_path()
            os.environ["PATH"] = "/x"
            restore_path(snap)
            assert os.environ["PATH"] == "/a:/b:/c"

    def test_snapshot_returns_list_of_strings(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            assert snapshot_path() == ["/a", "/b"]

    def test_snapshot_empty_path(self):
        with patch.dict(os.environ, {"PATH": ""}):
            assert snapshot_path() == []

    def test_restore_empty(self):
        with patch.dict(os.environ, {"PATH": "/a:/b"}):
            restore_path([])
            assert os.environ["PATH"] == ""
