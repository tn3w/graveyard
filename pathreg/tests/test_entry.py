from pathreg import _entry


class TestEntry:
    def test_basic_format(self):
        assert _entry("/usr/local/bin") == 'PATH="/usr/local/bin:$PATH"\n'

    def test_ends_with_newline(self):
        assert _entry("/foo").endswith("\n")

    def test_contains_dollar_path(self):
        assert "$PATH" in _entry("/foo")

    def test_contains_directory(self):
        assert "/my/custom/dir" in _entry("/my/custom/dir")

    def test_starts_with_quoted_path_assignment(self):
        assert _entry("/some/path").startswith('PATH="')

    def test_different_directories_produce_different_entries(self):
        assert _entry("/foo") != _entry("/bar")

    def test_path_with_spaces(self):
        assert "/path with spaces" in _entry("/path with spaces")

    def test_home_directory(self):
        assert "/home/user/bin" in _entry("/home/user/bin")
