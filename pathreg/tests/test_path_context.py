import os
from unittest.mock import patch

import pytest

from pathreg import path_context


class TestPathContext:
    def test_adds_and_restores(self, tmp_path):
        original = os.environ.get("PATH", "")
        with (
            patch("pathreg._shell", return_value="sh"),
            patch("pathreg._profile", return_value=tmp_path / ".profile"),
        ):
            with path_context("/tmp/ctx_test_dir"):
                assert "/tmp/ctx_test_dir" in os.environ["PATH"]
        assert os.environ["PATH"] == original

    def test_restores_on_exception(self, tmp_path):
        original = os.environ.get("PATH", "")
        with pytest.raises(ValueError):
            with (
                patch("pathreg._shell", return_value="sh"),
                patch("pathreg._profile", return_value=tmp_path / ".profile"),
            ):
                with path_context("/tmp/ctx_exc_dir"):
                    raise ValueError("oops")
        assert os.environ["PATH"] == original

    def test_multiple_directories(self, tmp_path):
        original = os.environ.get("PATH", "")
        with (
            patch("pathreg._shell", return_value="sh"),
            patch("pathreg._profile", return_value=tmp_path / ".profile"),
        ):
            with path_context("/tmp/dir1", "/tmp/dir2"):
                assert "/tmp/dir1" in os.environ["PATH"]
                assert "/tmp/dir2" in os.environ["PATH"]
        assert os.environ["PATH"] == original

    def test_returns_self_on_enter(self, tmp_path):
        with (
            patch("pathreg._shell", return_value="sh"),
            patch("pathreg._profile", return_value=tmp_path / ".profile"),
        ):
            ctx = path_context("/tmp/x")
            result = ctx.__enter__()
            ctx.__exit__(None, None, None)
        assert result is ctx
