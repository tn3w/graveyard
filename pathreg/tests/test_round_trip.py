import os
from unittest.mock import patch

from pathreg import _add_path_unix, _entry, _remove_path_unix, main


class TestRoundTrip:
    def test_add_then_remove_leaves_profile_unchanged(self, sh_profile):
        original = "export EDITOR=vim\n"
        sh_profile.write_text(original)
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/tmp/bin")
            _remove_path_unix("/tmp/bin")
        assert sh_profile.read_text() == original

    def test_add_then_remove_restores_environ_path(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/tmp/bin")
            assert "/tmp/bin" in os.environ["PATH"]
            _remove_path_unix("/tmp/bin")
            assert "/tmp/bin" not in os.environ["PATH"]

    def test_add_same_dir_twice_then_remove(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/tmp/bin")
            _add_path_unix("/tmp/bin")
            assert sh_profile.read_text().count(_entry("/tmp/bin")) == 1
            _remove_path_unix("/tmp/bin")
        assert _entry("/tmp/bin") not in sh_profile.read_text()

    def test_multiple_dirs_remove_one(self, sh_profile):
        with patch.dict(os.environ, {"PATH": "/existing"}):
            _add_path_unix("/dir/a")
            _add_path_unix("/dir/b")
            _remove_path_unix("/dir/a")
        content = sh_profile.read_text()
        assert _entry("/dir/a") not in content
        assert _entry("/dir/b") in content

    def test_via_main_add_then_remove(self, sh_profile):
        original = "# existing config\n"
        sh_profile.write_text(original)

        with (
            patch("sys.argv", ["pathreg", "add", "/rnd/dir"]),
            patch.dict(os.environ, {"PATH": "/existing"}),
            patch("builtins.print"),
        ):
            main()

        with (
            patch("sys.argv", ["pathreg", "remove", "/rnd/dir"]),
            patch.dict(os.environ, {"PATH": "/rnd/dir:/existing"}),
            patch("builtins.print"),
        ):
            main()

        assert sh_profile.read_text() == original
