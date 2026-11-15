import os
from unittest.mock import patch

from pathreg import _add_path_unix, _entry


class TestAddPathUnix:
    def test_adds_entry_to_empty_profile(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
        assert _entry("/new/dir") in sh_profile.read_text()

    def test_appends_entry_to_existing_profile(self, sh_profile):
        sh_profile.write_text("export EDITOR=vim\n")
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
        content = sh_profile.read_text()
        assert "export EDITOR=vim\n" in content
        assert _entry("/new/dir") in content

    def test_does_not_duplicate_existing_entry(self, sh_profile):
        sh_profile.write_text(_entry("/new/dir"))
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
        assert sh_profile.read_text().count(_entry("/new/dir")) == 1

    def test_updates_os_environ_path(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
            assert "/new/dir" in os.environ["PATH"]

    def test_new_dir_appended_in_environ(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
            assert os.environ["PATH"].endswith(":/new/dir")

    def test_strips_trailing_slash(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir/")
        content = sh_profile.read_text()
        assert _entry("/new/dir") in content
        assert _entry("/new/dir/") not in content

    def test_strips_leading_whitespace(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("  /new/dir")
        assert _entry("/new/dir") in sh_profile.read_text()

    def test_converts_backslash_to_forward_slash(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("\\new\\dir")
        assert _entry("/new/dir") in sh_profile.read_text()

    def test_creates_profile_file_if_missing(self, sh_profile):
        assert not sh_profile.exists()
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
        assert sh_profile.exists()

    def test_idempotent_with_trailing_slash_variant(self, sh_profile):
        sh_profile.write_text(_entry("/new/dir"))
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir/")
        assert sh_profile.read_text().count(_entry("/new/dir")) == 1

    def test_only_one_trailing_slash_stripped(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir//")
        assert _entry("/new/dir/") in sh_profile.read_text()

    def test_environ_unchanged_when_entry_already_in_profile(self, sh_profile):
        sh_profile.write_text(_entry("/new/dir"))
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir")
            assert os.environ["PATH"] == "/existing"

    def test_multiple_different_dirs(self, sh_profile):
        for d in ["/first", "/second", "/third"]:
            with patch.dict(os.environ, {"PATH": "/existing"}):
                _add_path_unix(d)
        content = sh_profile.read_text()
        for d in ["/first", "/second", "/third"]:
            assert _entry(d) in content

    def test_empty_path_env_var(self, sh_profile):
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        with patch.dict(os.environ, env, clear=True):
            _add_path_unix("/new/dir")
            assert os.environ["PATH"].startswith("/new/dir")

    def test_strips_trailing_whitespace(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/new/dir  ")
        assert _entry("/new/dir") in sh_profile.read_text()
        assert _entry("/new/dir  ") not in sh_profile.read_text()
