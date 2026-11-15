import inspect
import os
import runpy
import sys
from unittest.mock import MagicMock, patch

import pathreg

WIN_SEP = ";"


def make_reg_path(value):
    return MagicMock(return_value=value)


def reg_patches(reg_path_value):
    reg_path = make_reg_path(reg_path_value)
    reg_set = MagicMock()
    return (
        reg_path,
        reg_set,
        [
            patch("pathreg._reg_path", reg_path, create=True),
            patch("pathreg._reg_set", reg_set, create=True),
            patch.object(os, "pathsep", WIN_SEP),
        ],
    )


class TestAddPathWindows:
    def test_adds_new_dir_to_environ(self):
        existing = WIN_SEP.join([r"C:\Windows\System32"])
        _, _, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows(r"C:\new\bin")
                assert r"C:\new\bin" in os.environ["PATH"]

    def test_calls_reg_set_with_new_entry_appended(self):
        existing = r"C:\Windows\System32"
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows(r"C:\new\bin")
        reg_set.assert_called_once()
        written = reg_set.call_args[0][0]
        assert written.endswith(r"C:\new\bin")

    def test_explicit_index_inserts_at_position(self):
        existing = WIN_SEP.join([r"C:\a", r"C:\b"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows(r"C:\new\bin", index=0)
        written = reg_set.call_args[0][0]
        assert written.startswith(r"C:\new\bin")

    def test_does_not_duplicate_existing_entry(self):
        existing = WIN_SEP.join([r"C:\new\bin", r"C:\Windows\System32"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows(r"C:\new\bin")
        reg_set.assert_not_called()

    def test_converts_forward_slashes(self):
        existing = r"C:\Windows\System32"
        _, _, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows("C:/new/bin")
                assert r"C:\new\bin" in os.environ["PATH"]

    def test_strips_trailing_backslash(self):
        existing = r"C:\Windows\System32"
        _, _, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows(r"C:\new\bin\ ".strip())
                assert r"C:\new\bin" in os.environ["PATH"]

    def test_recognises_existing_entry_with_trailing_backslash(self):
        existing = WIN_SEP.join([r"C:\new\bin" + "\\", r"C:\Windows\System32"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._add_path_windows(r"C:\new\bin")
        reg_set.assert_not_called()


class TestRemovePathWindows:
    def test_removes_from_registry(self):
        existing = WIN_SEP.join([r"C:\old\bin", r"C:\Windows\System32"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._remove_path_windows(r"C:\old\bin")
        written = reg_set.call_args[0][0]
        assert r"C:\old\bin" not in written.split(WIN_SEP)

    def test_keeps_other_entries_in_registry(self):
        existing = WIN_SEP.join([r"C:\old\bin", r"C:\keep\this"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._remove_path_windows(r"C:\old\bin")
        written = reg_set.call_args[0][0]
        assert r"C:\keep\this" in written

    def test_converts_forward_slashes(self):
        existing = WIN_SEP.join([r"C:\old\bin", r"C:\Windows\System32"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._remove_path_windows("C:/old/bin")
        written = reg_set.call_args[0][0]
        assert r"C:\old\bin" not in written.split(WIN_SEP)

    def test_removes_entry_with_trailing_backslash_in_registry(self):
        existing = WIN_SEP.join([r"C:\old\bin\ ", r"C:\Windows\System32"])
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._remove_path_windows(r"C:\old\bin")
        written = reg_set.call_args[0][0]
        remaining = [p.removesuffix("\\").strip() for p in written.split(WIN_SEP)]
        assert r"C:\old\bin" not in remaining


class TestSetPathWindows:
    def test_replaces_registry_with_given_dirs(self):
        existing = r"C:\old\bin"
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._set_path_windows([r"C:\new\a", r"C:\new\b"])
        written = reg_set.call_args[0][0]
        assert written == WIN_SEP.join([r"C:\new\a", r"C:\new\b"])

    def test_updates_environ_path(self):
        existing = r"C:\old\bin"
        _, _, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {}, clear=True):
                os.environ["PATH"] = existing
                pathreg._set_path_windows([r"C:\new\a"])
                assert os.environ["PATH"] == r"C:\new\a"

    def test_converts_forward_slashes(self):
        existing = r"C:\old"
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._set_path_windows(["C:/new/a"])
        written = reg_set.call_args[0][0]
        assert written == r"C:\new\a"

    def test_strips_trailing_backslash(self):
        existing = r"C:\old"
        _, reg_set, patches = reg_patches(existing)
        with patches[0], patches[1], patches[2]:
            with patch.dict(os.environ, {"PATH": existing}):
                pathreg._set_path_windows([r"C:\new\a\ ".strip()])
        written = reg_set.call_args[0][0]
        assert written == r"C:\new\a"


class TestWindowsModuleInit:
    def test_windows_imports_define_reg_helpers(self):
        winreg_mock = MagicMock()
        key_ctx = MagicMock()
        key_ctx.__enter__ = MagicMock(return_value=winreg_mock)
        key_ctx.__exit__ = MagicMock(return_value=False)
        winreg_mock.OpenKey.return_value = key_ctx
        winreg_mock.QueryValueEx.return_value = (r"C:\Windows\System32", 1)
        winreg_mock.HKEY_CURRENT_USER = 0x80000001
        winreg_mock.KEY_SET_VALUE = 2
        winreg_mock.REG_EXPAND_SZ = 2

        ctypes_mock = MagicMock()
        ctypes_mock.windll.user32.SendMessageTimeoutW.return_value = 1

        source_path = inspect.getfile(pathreg)
        with (
            patch.object(sys, "platform", "win32"),
            patch.dict(sys.modules, {"winreg": winreg_mock, "ctypes": ctypes_mock}),
        ):
            ns = runpy.run_path(source_path)

        assert "_reg_path" in ns
        assert "_reg_set" in ns
        assert callable(ns["_reg_path"])
        assert callable(ns["_reg_set"])

    def test_reg_path_reads_from_registry(self):
        winreg_mock = MagicMock()
        key_ctx = MagicMock()
        key_ctx.__enter__ = MagicMock(return_value=winreg_mock)
        key_ctx.__exit__ = MagicMock(return_value=False)
        winreg_mock.OpenKey.return_value = key_ctx
        winreg_mock.QueryValueEx.return_value = (r"C:\Windows\System32", 1)
        winreg_mock.HKEY_CURRENT_USER = 0x80000001
        winreg_mock.KEY_SET_VALUE = 2
        winreg_mock.REG_EXPAND_SZ = 2

        ctypes_mock = MagicMock()

        source_path = inspect.getfile(pathreg)
        with (
            patch.object(sys, "platform", "win32"),
            patch.dict(sys.modules, {"winreg": winreg_mock, "ctypes": ctypes_mock}),
        ):
            ns = runpy.run_path(source_path)

        result = ns["_reg_path"]()
        assert result == r"C:\Windows\System32"

    def test_reg_set_writes_to_registry_and_notifies(self):
        winreg_mock = MagicMock()
        key_ctx = MagicMock()
        key_ctx.__enter__ = MagicMock(return_value=winreg_mock)
        key_ctx.__exit__ = MagicMock(return_value=False)
        winreg_mock.OpenKey.return_value = key_ctx
        winreg_mock.QueryValueEx.return_value = (r"C:\Windows\System32", 1)
        winreg_mock.HKEY_CURRENT_USER = 0x80000001
        winreg_mock.KEY_SET_VALUE = 2
        winreg_mock.REG_EXPAND_SZ = 2

        ctypes_mock = MagicMock()
        send_msg = ctypes_mock.windll.user32.SendMessageTimeoutW

        source_path = inspect.getfile(pathreg)
        with (
            patch.object(sys, "platform", "win32"),
            patch.dict(sys.modules, {"winreg": winreg_mock, "ctypes": ctypes_mock}),
        ):
            ns = runpy.run_path(source_path)

        ns["_reg_set"](r"C:\new\bin;C:\Windows\System32")
        winreg_mock.SetValueEx.assert_called_once()
        send_msg.assert_called_once()
