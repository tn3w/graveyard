from pathlib import Path

from pathreg import diff_paths


class TestDiffPaths:
    def test_added(self):
        result = diff_paths(
            [Path("/a"), Path("/b")], [Path("/a"), Path("/b"), Path("/c")]
        )
        assert result == {"added": [Path("/c")], "removed": []}

    def test_removed(self):
        result = diff_paths([Path("/a"), Path("/b")], [Path("/a")])
        assert result == {"added": [], "removed": [Path("/b")]}

    def test_unchanged(self):
        paths = [Path("/a"), Path("/b")]
        assert diff_paths(paths, paths) == {"added": [], "removed": []}

    def test_order_preserved_in_added(self):
        result = diff_paths([Path("/a")], [Path("/c"), Path("/b"), Path("/a")])
        assert result["added"] == [Path("/c"), Path("/b")]

    def test_both_added_and_removed(self):
        result = diff_paths([Path("/a"), Path("/b")], [Path("/b"), Path("/c")])
        assert result["added"] == [Path("/c")]
        assert result["removed"] == [Path("/a")]
