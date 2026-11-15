import os
from unittest.mock import patch

from pathreg import _shell


class TestShell:
    def test_returns_last_segment_of_shell_path(self):
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            assert _shell() == "bash"

    def test_returns_last_segment_zsh(self):
        with patch.dict(os.environ, {"SHELL": "/usr/bin/zsh"}):
            assert _shell() == "zsh"

    def test_returns_last_segment_sh(self):
        with patch.dict(os.environ, {"SHELL": "/bin/sh"}):
            assert _shell() == "sh"

    def test_returns_bare_name_without_slash(self):
        with patch.dict(os.environ, {"SHELL": "fish"}):
            assert _shell() == "fish"

    def test_empty_shell_env_returns_empty_string(self):
        env = {k: v for k, v in os.environ.items() if k != "SHELL"}
        with patch.dict(os.environ, env, clear=True):
            assert _shell() == ""

    def test_deeply_nested_path(self):
        with patch.dict(os.environ, {"SHELL": "/usr/local/bin/bash"}):
            assert _shell() == "bash"

    def test_shell_with_version_suffix(self):
        with patch.dict(os.environ, {"SHELL": "/usr/bin/zsh5"}):
            assert _shell() == "zsh5"

    def test_empty_string_shell_returns_empty_string(self):
        with patch.dict(os.environ, {"SHELL": ""}):
            assert _shell() == ""
