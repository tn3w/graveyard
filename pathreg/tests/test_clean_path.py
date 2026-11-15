import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from pathreg import clean_path, main


class TestCleanPath:
    def test_removes_nonexistent_directory(self, tmp_path):
        missing = str(tmp_path / "missing")
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", missing)
            result = clean_path()
        assert result == []
        assert missing not in os.environ["PATH"]

    def test_keeps_existing_directory(self, tmp_path):
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", str(tmp_path))
            result = clean_path()
        assert tmp_path in result

    def test_removes_duplicate_directories(self, tmp_path):
        raw = f"{tmp_path}:{tmp_path}"
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", raw)
            result = clean_path()
        assert result.count(tmp_path) == 1

    def test_removes_duplicate_via_symlink(self, tmp_path):
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        link = tmp_path / "link"
        link.symlink_to(real_dir)
        raw = f"{real_dir}:{link}"
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", raw)
            result = clean_path()
        assert len(result) == 1

    def test_updates_os_environ(self, tmp_path):
        missing = str(tmp_path / "gone")
        raw = f"{missing}:{tmp_path}"
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", raw)
            clean_path()
            assert missing not in os.environ["PATH"]
            assert str(tmp_path) in os.environ["PATH"]

    def test_empty_path(self):
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", "")
            result = clean_path()
        assert result == []

    def test_path_not_set(self):
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        with pytest.MonkeyPatch().context() as mp:
            for key in list(os.environ):
                mp.delenv(key, raising=False)
            for k, v in env.items():
                mp.setenv(k, v)
            mp.delenv("PATH", raising=False)
            result = clean_path()
        assert result == []

    def test_preserves_order(self, tmp_path):
        dirs = [tmp_path / f"d{i}" for i in range(3)]
        for d in dirs:
            d.mkdir()
        raw = ":".join(str(d) for d in dirs)
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", raw)
            result = clean_path()
        assert result == dirs

    def test_skips_empty_segments(self, tmp_path):
        raw = f":{tmp_path}:"
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", raw)
            result = clean_path()
        assert result == [tmp_path]

    def test_cli_clean_prints_kept_paths(self, tmp_path):
        missing = str(tmp_path / "gone")
        raw = f"{tmp_path}:{missing}"
        with patch.object(sys, "argv", ["pathreg", "clean"]):
            with pytest.MonkeyPatch().context() as mp:
                mp.setenv("PATH", raw)
                captured = StringIO()
                with patch("sys.stdout", captured):
                    main()
        assert str(tmp_path) in captured.getvalue()
        assert missing not in captured.getvalue()

    def test_mixed_existing_and_missing(self, tmp_path):
        existing = tmp_path / "exists"
        existing.mkdir()
        missing = str(tmp_path / "missing")
        raw = f"{existing}:{missing}:{existing}"
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("PATH", raw)
            result = clean_path()
        assert result == [existing]
