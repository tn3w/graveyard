import os
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from pathreg import _entry, _set_path_unix, main, set_path


class TestSetPathUnix:
    def test_replaces_environ_path(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/old"}):
            _set_path_unix(["/new/a", "/new/b"])
            assert os.environ["PATH"] == "/new/a:/new/b"

    def test_writes_entries_to_profile(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/old"}):
            _set_path_unix(["/new/a", "/new/b"])
        content = sh_profile.read_text()
        assert _entry("/new/a") in content
        assert _entry("/new/b") in content

    def test_removes_previous_path_entries_from_profile(self, sh_profile):
        sh_profile.write_text(_entry("/old/a") + _entry("/old/b"))
        with patch.dict(os.environ, {"PATH": "/old/a:/old/b"}):
            _set_path_unix(["/new"])
        content = sh_profile.read_text()
        assert _entry("/old/a") not in content
        assert _entry("/old/b") not in content

    def test_removes_export_prefixed_entries_from_profile(self, sh_profile):
        sh_profile.write_text(f"export {_entry('/old')}")
        with patch.dict(os.environ, {"PATH": "/old"}):
            _set_path_unix(["/new"])
        assert _entry("/old") not in sh_profile.read_text()

    def test_preserves_non_path_profile_content(self, sh_profile):
        sh_profile.write_text("export EDITOR=vim\n" + _entry("/old"))
        with patch.dict(os.environ, {"PATH": "/old"}):
            _set_path_unix(["/new"])
        assert "export EDITOR=vim\n" in sh_profile.read_text()

    def test_creates_profile_if_missing(self, sh_profile):
        assert not sh_profile.exists()
        with patch.dict(os.environ, {"PATH": "/old"}):
            _set_path_unix(["/new"])
        assert sh_profile.exists()

    def test_empty_list_clears_path(self, sh_profile):
        sh_profile.write_text(_entry("/old"))
        with patch.dict(os.environ, {}, clear=True):
            os.environ["PATH"] = "/old"
            _set_path_unix([])
            assert os.environ["PATH"] == ""
        assert _entry("/old") not in sh_profile.read_text()

    def test_strips_trailing_slash(self, sh_profile):
        with patch.dict(os.environ, {"PATH": ""}):
            _set_path_unix(["/new/dir/"])
        assert _entry("/new/dir") in sh_profile.read_text()
        assert _entry("/new/dir/") not in sh_profile.read_text()

    def test_strips_whitespace(self, sh_profile):
        with patch.dict(os.environ, {"PATH": ""}):
            _set_path_unix(["  /new/dir  "])
        assert _entry("/new/dir") in sh_profile.read_text()

    def test_single_directory(self, sh_profile):
        with patch.dict(os.environ, {}, clear=True):
            os.environ["PATH"] = "/old"
            _set_path_unix(["/only"])
            assert os.environ["PATH"] == "/only"


class TestSetPathAlias:
    def test_set_path_is_unix_on_non_windows(self):
        assert set_path is _set_path_unix


class TestSetPathCLI:
    def test_cli_set_updates_environ(self, sh_profile):
        with patch.object(sys, "argv", ["pathreg", "set", "/a", "/b"]):
            with patch.dict(os.environ, {"PATH": "/old"}):
                main()
                assert os.environ["PATH"] == "/a:/b"

    def test_cli_set_prints_confirmation(self, sh_profile):
        with patch.object(sys, "argv", ["pathreg", "set", "/a", "/b"]):
            with patch.dict(os.environ, {"PATH": "/old"}):
                captured = StringIO()
                with patch("sys.stdout", captured):
                    main()
        assert "/a" in captured.getvalue()
        assert "/b" in captured.getvalue()

    def test_cli_set_requires_at_least_one_directory(self):
        with patch.object(sys, "argv", ["pathreg", "set"]):
            with pytest.raises(SystemExit):
                main()
