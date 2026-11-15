import os
from unittest.mock import patch

import pytest


@pytest.fixture
def profile(tmp_path):
    return tmp_path / ".profile"


@pytest.fixture
def sh_profile(profile):
    """Patch shell to 'sh' and _profile to a temp file."""
    with (
        patch("pathreg._shell", return_value="sh"),
        patch("pathreg._profile", return_value=profile),
    ):
        yield profile
