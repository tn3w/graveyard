import os
from unittest.mock import patch

from pathreg import load_path_from_file, save_path_to_file


class TestSavePathToFile:
    def test_writes_one_entry_per_line(self, tmp_path):
        file = tmp_path / "paths.txt"
        with patch.dict(os.environ, {"PATH": "/a:/b:/c"}):
            save_path_to_file(file)
        assert file.read_text().splitlines() == ["/a", "/b", "/c"]

    def test_accepts_path_object(self, tmp_path):
        file = tmp_path / "out.txt"
        with patch.dict(os.environ, {"PATH": "/x"}):
            save_path_to_file(file)
        assert file.read_text().strip() == "/x"

    def test_accepts_string_path(self, tmp_path):
        file = tmp_path / "out.txt"
        with patch.dict(os.environ, {"PATH": "/y"}):
            save_path_to_file(str(file))
        assert "/y" in file.read_text()


class TestLoadPathFromFile:
    def test_adds_entries_from_file(self, tmp_path):
        file = tmp_path / "paths.txt"
        file.write_text("/a\n/b\n")
        original = os.environ.get("PATH", "")
        with (
            patch("pathreg._shell", return_value="sh"),
            patch("pathreg._profile", return_value=tmp_path / ".profile"),
        ):
            load_path_from_file(file)
        parts = os.environ["PATH"].split(":")
        assert "/a" in parts
        assert "/b" in parts
        os.environ["PATH"] = original

    def test_skips_empty_lines(self, tmp_path):
        file = tmp_path / "paths.txt"
        file.write_text("/a\n\n/b\n")
        original = os.environ.get("PATH", "")
        with (
            patch("pathreg._shell", return_value="sh"),
            patch("pathreg._profile", return_value=tmp_path / ".profile"),
        ):
            load_path_from_file(file)
        parts = os.environ["PATH"].split(":")
        assert "/a" in parts
        assert "/b" in parts
        os.environ["PATH"] = original
