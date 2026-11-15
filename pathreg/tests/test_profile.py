from pathlib import Path
from unittest.mock import patch

import pytest

from pathreg import _profile


class TestProfile:
    def test_bash_returns_existing_bash_profile(self, tmp_path):
        bash_profile = tmp_path / ".bash_profile"
        bash_profile.touch()
        profile_path = tmp_path / ".profile"
        profile_path.touch()

        with patch(
            "pathreg._PROFILES", {"bash": (str(bash_profile), str(profile_path))}
        ):
            assert _profile("bash") == bash_profile

    def test_bash_falls_back_to_profile_when_bash_profile_missing(self, tmp_path):
        bash_profile = tmp_path / ".bash_profile"
        profile_path = tmp_path / ".profile"
        profile_path.touch()

        with patch(
            "pathreg._PROFILES", {"bash": (str(bash_profile), str(profile_path))}
        ):
            assert _profile("bash") == profile_path

    def test_bash_returns_first_candidate_when_neither_exists(self, tmp_path):
        bash_profile = tmp_path / ".bash_profile"
        profile_path = tmp_path / ".profile"

        with patch(
            "pathreg._PROFILES", {"bash": (str(bash_profile), str(profile_path))}
        ):
            assert _profile("bash") == bash_profile

    def test_zsh_returns_zshenv(self, tmp_path):
        zshenv = tmp_path / ".zshenv"
        zshenv.touch()

        with patch("pathreg._PROFILES", {"zsh": (str(zshenv),)}):
            assert _profile("zsh") == zshenv

    def test_sh_returns_profile(self, tmp_path):
        profile_path = tmp_path / ".profile"
        profile_path.touch()

        with patch("pathreg._PROFILES", {"sh": (str(profile_path),)}):
            assert _profile("sh") == profile_path

    def test_unknown_shell_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Unsupported shell: fish"):
            _profile("fish")

    def test_unknown_shell_empty_string_raises(self):
        with pytest.raises(NotImplementedError):
            _profile("")

    def test_unknown_shell_powershell_raises(self):
        with pytest.raises(NotImplementedError):
            _profile("powershell")

    def test_returns_path_object(self, tmp_path):
        p = tmp_path / ".zshenv"
        p.touch()
        with patch("pathreg._PROFILES", {"zsh": (str(p),)}):
            assert isinstance(_profile("zsh"), Path)

    def test_prefers_first_existing_over_second(self, tmp_path):
        first = tmp_path / ".bash_profile"
        second = tmp_path / ".profile"
        first.touch()
        second.touch()

        with patch("pathreg._PROFILES", {"bash": (str(first), str(second))}):
            assert _profile("bash") == first

    def test_expands_tilde_in_candidate_path(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        profile = home / ".profile"
        profile.touch()

        with (
            patch("pathreg._PROFILES", {"sh": ("~/.profile",)}),
            patch("pathlib.Path.expanduser", return_value=profile),
        ):
            assert _profile("sh") == profile
