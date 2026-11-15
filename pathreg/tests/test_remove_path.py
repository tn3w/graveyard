import os
from unittest.mock import patch

from pathreg import _entry, _remove_path_unix


class TestRemovePathUnix:
    def test_removes_entry_from_profile(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
        assert _entry("/old/dir") not in sh_profile.read_text()

    def test_removes_only_target_entry(self, sh_profile):
        sh_profile.write_text(_entry("/keep/this") + _entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
        content = sh_profile.read_text()
        assert _entry("/keep/this") in content
        assert _entry("/old/dir") not in content

    def test_removes_export_prefixed_entry(self, sh_profile):
        sh_profile.write_text(f"export {_entry('/old/dir')}")
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
        assert "/old/dir" not in sh_profile.read_text()

    def test_does_nothing_when_profile_missing(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
        assert not sh_profile.exists()

    def test_profile_missing_leaves_environ_path_unchanged(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
            assert "/old/dir" in os.environ["PATH"]

    def test_only_one_trailing_slash_stripped(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir//")
        assert _entry("/old/dir") in sh_profile.read_text()

    def test_removes_from_os_environ_path(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
            assert "/old/dir" not in os.environ["PATH"]

    def test_keeps_other_paths_in_environ(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/keep/this"}):
            _remove_path_unix("/old/dir")
            assert "/keep/this" in os.environ["PATH"]

    def test_strips_trailing_slash_before_removing(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir/")
        assert _entry("/old/dir") not in sh_profile.read_text()

    def test_strips_whitespace_before_removing(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("  /old/dir  ")
        assert _entry("/old/dir") not in sh_profile.read_text()

    def test_converts_backslash_before_removing(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("\\old\\dir")
        assert _entry("/old/dir") not in sh_profile.read_text()

    def test_nonexistent_entry_leaves_profile_intact(self, sh_profile):
        original = _entry("/keep/this")
        sh_profile.write_text(original)
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _remove_path_unix("/not/here")
        assert sh_profile.read_text() == original

    def test_removes_all_occurrences(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir") + _entry("/old/dir"))
        with patch.dict(os.environ, {"PATH": "/old/dir:/existing"}):
            _remove_path_unix("/old/dir")
        assert _entry("/old/dir") not in sh_profile.read_text()

    def test_environ_path_without_target_unchanged(self, sh_profile):
        sh_profile.write_text("")
        with patch.dict(os.environ, {"PATH": "/keep/this:/and/this"}):
            _remove_path_unix("/not/in/path")
            assert os.environ["PATH"] == "/keep/this:/and/this"

    def test_removes_entry_in_middle_of_environ_path(self, sh_profile):
        sh_profile.write_text(_entry("/middle"))
        with patch.dict(os.environ, {"PATH": "/first:/middle:/last"}):
            _remove_path_unix("/middle")
            parts = os.environ["PATH"].split(":")
            assert "/middle" not in parts
            assert "/first" in parts
            assert "/last" in parts

    def test_no_path_env_var_does_not_raise(self, sh_profile):
        sh_profile.write_text(_entry("/old/dir"))
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        with patch.dict(os.environ, env, clear=True):
            _remove_path_unix("/old/dir")
        assert _entry("/old/dir") not in sh_profile.read_text()
