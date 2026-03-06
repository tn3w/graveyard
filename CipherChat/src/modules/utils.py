import os
import sys
import re
import json
import shutil
import tarfile
import struct
import subprocess
import math
from functools import wraps
from time import sleep, time
from html.parser import HTMLParser
from threading import Lock, Event, Thread
from typing import Tuple, Optional, Union, Callable
from contextlib import contextmanager
import concurrent.futures

if os.name == 'nt':
    from msvcrt import getch
    import ctypes
    import ctypes.wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    shell32 = ctypes.WinDLL('shell32', use_last_error=True)


    class ShellExecuteInfo(ctypes.Structure):
        """
        A ctypes structure used to specify information for
        executing a command via ShellExecuteEx.
        """

        _fields_ = [
            ('cbSize', ctypes.wintypes.DWORD),
            ('fMask', ctypes.wintypes.ULONG),
            ('hwnd', ctypes.wintypes.HANDLE),
            ('lpVerb', ctypes.wintypes.LPCWSTR),
            ('lpFile', ctypes.wintypes.LPCWSTR),
            ('lpParameters', ctypes.wintypes.LPCWSTR),
            ('lpDirectory', ctypes.wintypes.LPCWSTR),
            ('nShow', ctypes.c_int),
            ('hInstApp', ctypes.wintypes.HINSTANCE),
            ('lpIDList', ctypes.c_void_p),
            ('lpClass', ctypes.wintypes.LPCWSTR),
            ('hkeyClass', ctypes.wintypes.HKEY),
            ('dwHotKey', ctypes.wintypes.DWORD),
            ('hIcon', ctypes.wintypes.HANDLE),
            ('hProcess', ctypes.wintypes.HANDLE)
        ]

        def __init__(self, lpVerb: Optional[str] = None,
                     lpFile: Optional[str] = None,
                     nShow: Optional[int] = None):
            if None in [lpVerb, lpFile]:
                return

            self.cbSize = ctypes.sizeof(self)
            self.lpVerb = lpVerb
            self.lpFile = lpFile

            if not isinstance(nShow, int):
                nShow = 1

            self.nShow = nShow

    shell_execute_ex = shell32.ShellExecuteExW
    shell_execute_ex.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
    shell_execute_ex.restype = ctypes.wintypes.BOOL

    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    wait_for_single_object.restype = ctypes.wintypes.DWORD
else:
    import termios
    import tty
    import fcntl

try:
    from src.modules.cons import PASSWORD_REGEX, ENV, DELETION_FILE_BYTES, LOGO_BIG, LOGO_SMALL
except ImportError:
    from cons import PASSWORD_REGEX, ENV, DELETION_FILE_BYTES, LOGO_BIG, LOGO_SMALL


FILE_LOCKS: dict = {}


def get_parameters_after_argument(argument: str, all_arguments: list, ignore_dashes = True) -> list:
    """
    Retrieves the parameters following a specified argument from a list of all arguments.

    :param argument: The argument whose parameters are to be retrieved.
    :param all_arguments: A list of all arguments passed to a command or function.
    :return: A list containing the parameters that come after the specified argument.
             If the argument is not found in the list of all arguments or if there are
             no parameters following the argument, an empty list is returned.
    """

    if argument not in all_arguments:
        return []

    key_index = all_arguments.index(argument)

    if key_index + 1 < len(all_arguments):
        args_after_key = all_arguments[key_index + 1:]

        if ignore_dashes:
            next_dash_index = next(
                (i for i, arg in enumerate(args_after_key) if arg.startswith("yo"))
                , None)

            if next_dash_index is not None:
                return args_after_key[:next_dash_index]
        return args_after_key

    return []


def cache(seconds):
    """
    A decorator that stores the output of a function in cache for a specified duration.

    :param seconds: The duration in seconds for which the results will be stored in cache.
    :return: The decorator that can be applied to a function.
    """

    def decorator(func):
        cache_dict = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))

            if key in cache_dict:
                if int(time()) - cache_dict[key]["timestamp"] <= seconds:
                    return cache_dict[key]["value"]
                del cache_dict[key]

            result = func(*args, **kwargs)

            cache_dict[key] = {"value": result, "timestamp": int(time())}
            return result

        return wrapper

    return decorator


def get_password_strength(password: str) -> int:
    """
    Function to get a password strength from 0 (bad) to 100% (good)

    :param password: The password to check
    """

    strength = min((len(password) / 16) * 60, 60)

    for regex in PASSWORD_REGEX:
        if re.search(regex, password):
            strength += 10

    strength = min(strength, 100)
    return math.ceil(strength)


def run_command(command: list, shell: bool = False,
                as_admin: bool = False) -> Tuple[bool, str, int]:
    """
    Executes a system command and returns a tuple indicating success or failure,
    along with the standard error output and return code of the command.

    :param command: The system command to execute.
    :return: A tuple containing:
             - A boolean indicating whether an error occurred during command execution.
             - The standard error output (if any) produced by the command.
             - The return code of the command.
    """

    if as_admin and os.name == 'nt':
        if not ctypes.windll.shell32.IsUserAnAdmin():
            sei = ShellExecuteInfo('runas', ' '.join(command).strip())

            if not shell_execute_ex(ctypes.byref(sei)):
                return True, "Error", "Error", 2

            if sei.hProcess:
                wait_for_single_object(sei.hProcess, 0xFFFFFFFF)
            return False, "Done.", None, 0

    try:
        with subprocess.Popen(
            command, env = ENV, stdout = subprocess.PIPE,
            stderr = subprocess.PIPE, shell = shell) as process:

            stdout, stderr = process.communicate()
            return_code = process.returncode

            if isinstance(stdout, bytes):
                stdout = stdout.decode('utf-8', errors = 'ignore')
            if isinstance(stderr, bytes):
                stderr = stderr.decode('utf-8', errors = 'ignore')

            return False, stdout, stderr, return_code
    except (subprocess.CalledProcessError, PermissionError,
            subprocess.SubprocessError, subprocess.CalledProcessError,
            OSError, subprocess.TimeoutExpired) as exc:
        return True, None, exc, 2


def check_permissions(path: str, mode: str = 'r') -> bool:
    """
    Determines if a file can be accessed with the specified mode at the specified path.

    :param path: A string representing the file path to check.
    :param mode: A string representing the access mode. Default is 'w' for write access.
                 Possible values are:
                     - 'r': Check if the file is readable.
                     - 'w': Check if the file is writable.
                     - 'x': Check if the file is executable.
                     - 'rw': Check if the file is readable and writable.
                     - 'rx': Check if the file is readable and executable.
                     - 'wx': Check if the file is writable and executable.
    :return: Returns True if the file at the given path can be accessed with the
             specified mode, False otherwise.
    """

    if not os.path.isfile(path):
        path = os.path.dirname(path)
        while not os.path.isdir(path):
            if len(path) < 5:
                break

            path = os.path.dirname(path)

        if not os.path.isdir(path):
            return False

    modes = {
        'r': os.R_OK,
        'w': os.W_OK,
        'x': os.X_OK,
        'rw': os.R_OK | os.W_OK,
        'rx': os.R_OK | os.X_OK,
        'wx': os.W_OK | os.X_OK,
    }

    used_mode = modes.get(mode, os.R_OK)

    return os.access(path, used_mode)


def get_recycle_bin_path(operating_system: str) -> Optional[str]:
    """
    Retrieves the path to the recycle bin directory based on the specified operating system.

    :param operating_system: A string indicating the operating system.
                             Accepted values are 'Windows', 'Linux', or 'macOS'.
    :return: The path to the recycle bin directory if found, otherwise None.
    """

    if operating_system == 'Windows':
        drives = ['C:\\', 'D:\\']
        for drive in drives:
            recycle_bin = os.path.join(drive, '$RECYCLE.BIN')
            if os.path.exists(recycle_bin):
                return recycle_bin
    elif operating_system in ['Linux', 'macOS']:
        return os.path.join(os.path.expanduser('~'), '.local', 'share', 'Trash')
    return None


def extract_tar(archive_file_path: str, directory_path: str) -> None:
    """
    Extracts a tar archive to the specified directory.

    :param archive_file_path: The path to the tar archive.
    :param directory_path: The directory where the contents of the tar archive will be extracted.
    :return: None
    """

    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    if not check_permissions(archive_file_path, 'r'):
        return

    with tarfile.open(archive_file_path, 'r') as tar:
        tar.extractall(directory_path, filter = 'data')


def read(
        file_path: str,
        is_bytes: bool = False,
        default: any = None
        ) -> any:
    """
    Reads the content of a file and returns it as either a string or bytes,
    depending on the 'is_bytes' parameter.
    
    :param file_path: The path of the file to be read.
    :param is_bytes: If True, the content will be returned as bytes; if False,
                     the content will be returned as a string.
    :param default: The value to return if the file does not exist or
                    cannot be read. Defaults to None.
    """

    if not os.path.isfile(file_path) or not check_permissions(file_path):
        return default

    if file_path not in FILE_LOCKS:
        FILE_LOCKS[file_path] = Lock()

    with FILE_LOCKS[file_path]:
        with open(file_path, 'r' + ('b' if is_bytes else ''),
            encoding = (None if is_bytes else 'utf-8')) as readable_file:
            file_content = readable_file.read()
    return file_content


def write(
        data: any,
        file_path: str,
        is_bytes: bool = False
        ) -> bool:
    """
    Writes data to a file, either as bytes or as a string, depending on the 'is_bytes' parameter.

    :param data: The data to be written to the file.
    :param file_path: The path of the file to write to.
    :param is_bytes: If True, the data will be written as bytes;
                     if False, the data will be written as a string.
    """

    file_directory = os.path.dirname(file_path)
    if not os.path.isdir(file_directory) or not check_permissions(file_path, 'w'):
        return False

    if file_path not in FILE_LOCKS:
        FILE_LOCKS[file_path] = Lock()

    with FILE_LOCKS[file_path]:
        with open(file_path, 'w' + ('b' if is_bytes else ''),
            encoding = (None if is_bytes else 'utf-8')) as writeable_file:
            writeable_file.write(data)
    return True


class JSON:
    "Class for loading / saving JavaScript Object Notation (= JSON)"

    @staticmethod
    def load(file_path: str, default: Optional[Union[dict, list]] = None) -> Union[dict, list]:
        """
        Function to load a JSON file securely.

        :param file_path: The file path to save to
        :param default: Returned if no data was found
        """

        if not os.path.isfile(file_path) or\
            not check_permissions(file_path, 'w'):

            if default is None:
                return {}
            return default

        if file_path not in FILE_LOCKS:
            FILE_LOCKS[file_path] = Lock()

        with FILE_LOCKS[file_path]:
            with open(file_path, "r", encoding = "utf-8") as file:
                data = json.load(file)

        return data

    @staticmethod
    def dump(data: Union[dict, list], file_path: str) -> bool:
        """
        Function to save a JSON file securely.
        
        :param data: The data to be stored should be either dict or list
        :param file_path: The file path to save to
        :return: Bool that says if the dump process was successful
        """

        file_directory = os.path.dirname(file_path)
        if not os.path.isdir(file_directory) or\
            not check_permissions(file_path, 'w'):
            return False

        if file_path not in FILE_LOCKS:
            FILE_LOCKS[file_path] = Lock()

        with FILE_LOCKS[file_path]:
            with open(file_path, "w", encoding = "utf-8") as file:
                json.dump(data, file)

        return True


class SecureDelete:
    "Class for secure deletion of files or folders"

    @staticmethod
    def list_files_and_directories(directory_path: str) -> Tuple[list, list]:
        """
        Function to get all files and directorys in a directory

        :param directory_path: The path to the directory
        """

        all_files = []
        all_directories = []

        def list_files_recursive(root, depth):
            try:
                for item in os.listdir(root):
                    item_path = os.path.join(root, item)
                    if os.path.isfile(item_path):
                        all_files.append((item_path, depth))
                    elif os.path.isdir(item_path):
                        all_directories.append((item_path, depth))
                        list_files_recursive(item_path, depth + 1)
            except PermissionError:
                pass

        list_files_recursive(directory_path, 0)

        all_files.sort(key=lambda x: x[1], reverse=True)
        all_directories.sort(key=lambda x: x[1], reverse=True)

        all_files = [path for path, _ in all_files]
        all_directories = [path for path, _ in all_directories]

        return all_files, all_directories

    @staticmethod
    def file(file_path: str, gutmann_patterns: list, dod_patterns: list) -> None:
        """
        Function to securely delete a file by replacing it first with random characters and
        then according to Gutmann patterns and DoD 5220.22-M patterns

        :param file_path: The path to the file
        :param quite: If True nothing is written to the console
        """

        if not check_permissions(file_path, 'w'):
            return

        for _ in range(4):
            if os.path.isfile(file_path):
                os.remove(file_path)

            for deletion_type in ['gutmann', 'dod', 'random']:
                pattern_lists = {'gutmann': gutmann_patterns, 'dod': dod_patterns}

                if deletion_type in pattern_lists:
                    for pattern in pattern_lists[deletion_type]:
                        write(pattern, file_path, True)
                        os.remove(file_path)
                elif deletion_type == 'random':
                    write(os.urandom(DELETION_FILE_BYTES), file_path, True)
                    os.remove(file_path)

    @staticmethod
    def directory(directory_path: str) -> bool:
        """
        Securely deletes entire folders with files and subfolders

        :param directory_path: The path to the directory
        """

        files, directories = SecureDelete.list_files_and_directories(directory_path)

        gutmann_patterns = [bytes([i % 256] * (DELETION_FILE_BYTES)) for i in range(35)]
        dod_patterns = [
            bytes([0x00] * DELETION_FILE_BYTES),
            bytes([0xFF] * DELETION_FILE_BYTES),
            bytes([0x00] * DELETION_FILE_BYTES)
        ]

        if len(files) == 1:
            SecureDelete.file(files[0], gutmann_patterns, dod_patterns)
        elif len(files) > 0:
            with concurrent.futures.ThreadPoolExecutor(
                min(len(files), (os.cpu_count() or 1) + 4)
                ) as executor:
                file_futures = {executor.submit(
                    SecureDelete.file, file, gutmann_patterns, dod_patterns
                    ): file for file in files}

                concurrent.futures.wait(file_futures)

        for directory in directories:
            try:
                shutil.rmtree(directory)
            except PermissionError:
                pass

        try:
            shutil.rmtree(directory_path)
        except PermissionError:
            return True

        return False


def is_character_supported(char: str) -> bool:
    """
    Checks if a given character is supported by the current system's encoding.

    :param char: The character to be tested for support.
    :return: True if the character is supported, False otherwise.
    """

    try:
        sys.stdout.write(char)
        sys.stdout.flush()

        test_char = char.encode(sys.stdout.encoding)
        decoded_char = test_char.decode(sys.stdout.encoding)
        return decoded_char == char
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    return False


def special_print(text: str, with_sys: bool = False,
                  end: Optional[str] = None, flush: bool = False) -> None:
    """
    Prints colored text to the console based on color tags
    provided within square brackets in the text.

    :param text: The text to be printed with optional color tags.
    """

    color_map = {
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'reset': '\033[39m'
    }

    result = ""
    current_color = None
    in_color_tag = False
    tag_buffer = ""

    for char in text:
        if char == '[':
            in_color_tag = True
            tag_buffer = ""
        elif char == ']' and in_color_tag:
            in_color_tag = False
            if tag_buffer.lower() in color_map:
                current_color = color_map[tag_buffer.lower()]
            else:
                result += '[' + tag_buffer + ']'

            if not current_color is None:
                result += current_color
        elif in_color_tag:
            tag_buffer += char
        else:
            if current_color:
                result += current_color
            result += char

    if '[' in text:
        result += color_map['reset']

    if with_sys:
        sys.stdout.write('\r' + result)
        sys.stdout.flush()
        return

    if flush:
        result = '\r' + ' ' * len(result) + '\r' + result

    print(result, end = end, flush = flush)


def get_window_size_ioctl(file_descriptor: int) -> Optional[Tuple[int, int]]:
    """
    Retrieves the size of the console window using IOCTL.

    :param file_descriptor: File descriptor of the terminal.
    :return: A tuple (rows, cols) representing the size of the console window,
             or None if the size cannot be determined.
    """

    if os.name == 'nt':
        raise OSError('Function `get_window_size_ioctl` should not be used on Windows')

    try:
        rows, cols = struct.unpack('hh', fcntl.ioctl(file_descriptor, termios.TIOCGWINSZ, '1234'))
        return rows, cols
    except (OSError, IOError):
        return None


def get_console_size() -> Tuple[int, int]:
    """
    Retrieves the size of the console window.

    :return: A tuple (rows, cols) representing the size of the console window.
    """

    window_size = None

    if not os.name == 'nt':
        window_size = get_window_size_ioctl(0) or get_window_size_ioctl(1)\
                      or get_window_size_ioctl(2)

        if not window_size:
            try:
                terminal_fd = os.open(os.ctermid(), os.O_RDONLY)
                window_size = get_window_size_ioctl(terminal_fd)
                os.close(terminal_fd)
            except (OSError, IOError):
                pass

    if window_size is None:
        terminal_size = os.get_terminal_size()
        window_size = (terminal_size.lines, terminal_size.columns)

    return window_size[0], window_size[1]


def clear_console(display_logo: bool = True):
    """
    Cleans the console and shows logo

    :param display_logo: Whether the logo should also be displayed
    """

    os.system('cls' if os.name == 'nt' else 'clear')

    if not display_logo:
        return

    _, console_columns = get_console_size()

    if console_columns > 104:
        print(LOGO_BIG)
    elif console_columns > 71:
        print(LOGO_SMALL)
    else:
        print('-~- CIPHERCHAT -~-\n')


def selection(options: list[str], subject: Optional[str] = None,
              text_until_now: Optional[str] = None,
              max_display: Optional[int] = None) -> str:
    """
    Displays a selection menu with the given options and prompts the user to choose one.
    
    :param options: A list of strings representing the options to choose from.
    :param subject: The subject or category of the selection (default is None).
    :param text_until_now: Text to display above the selection menu (default is None).
    :return: The selected option.
    """

    if max_display is None:
        max_display = len(options)

    selected_option = 0

    if not isinstance(subject, str):
        subject = 'one'

    while True:
        clear_console()
        if text_until_now is not None:
            special_print(text_until_now + '\n')

        for i, option in enumerate(options):
            if i >= max_display:
                continue

            if i == selected_option:
                print(f'[>] {option}')
            else:
                print(f'[ ] {option}')

        if max_display < len(options):
            show_more_string = 'Show ' + str(len(options) - max_display) + ' more'

            if selected_option == max_display:
                print('[>] ' + show_more_string)
            else:
                print('[ ] ' + show_more_string)

        key = input(f'\nChoose {subject} (Enter to go down; c to confirm): ')
        if not key.lower().startswith('c'):
            option_len = max_display
            if max_display < len(options):
                option_len += 1

            if option_len < selected_option + 2:
                selected_option = 0
            else:
                selected_option += 1
        else:
            if selected_option == max_display:
                max_display = len(options)
                continue
            return options[selected_option]


def pwd_input(message: str, replacement: str = '*') -> str:
    """
    Prompts the user with a message and reads input
    from the console, masking it with a replacement character.

    :param message: The message to display to the user.
    :param replacement: The character used to replace input characters. Defaults to '*'.
    :return: The user input as a string.
    """

    print(message, end='', flush=True)
    chars = ''

    while True:
        if os.name == 'nt':
            char = getch()
        else:
            fileno = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fileno)
            try:
                tty.setcbreak(fileno)
                char = sys.stdin.buffer.read(1)
            finally:
                termios.tcsetattr(fileno, termios.TCSADRAIN, old_settings)

        if char in {b'\n', b'\r', b'\r\n'}:
            print('')
            break

        if char == b'\x03':
            raise KeyboardInterrupt

        if char in {b'\x08', b'\x7f'}:
            chars = chars[:-1]

            padding_length = len(message) + len(chars) + 1
            formatted_output = "\r" + " " * padding_length + "\r"\
                            + message + replacement * len(chars)
            print(formatted_output, end='', flush=True)
        else:
            try:
                chars += char.decode('utf-8')
            except UnicodeDecodeError:
                continue

            print(replacement, end='', flush=True)

    return chars


class StatusSpinner:
    """
    A class for displaying a spinning animation to indicate ongoing progress.
    """

    def __init__(self, message: str):
        """
        Initializes the StatusSpinner object.

        :param message: The message to display alongside the spinner.
        """

        self.message = message + '[reset]'
        self.stop_event = Event()
        self.spinner_thread = Thread(target=self._run_spinner)

    def _run_spinner(self):
        """
        Runs the spinner animation in a separate thread.
        """

        all_spinners: list[list[str]] = [
            ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
            ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'],
            ['◐', '◓', '◑', '◒'],
            ['-', '\\', '|', '/'],
            ['-', 'o', '=', '*']
        ]
        choosen_spinner = None
        sleep_time: float = 0.15

        for spinner in all_spinners:
            is_supported = True
            for char in spinner:
                is_supported = is_character_supported(char)
                if not is_supported:
                    break

            if is_supported:
                choosen_spinner = spinner
                break
            sleep_time += 0.05

        if choosen_spinner is None:
            choosen_spinner = ['-', '\\', '|', '/']

        sleep_time = min(sleep_time, 0.3)

        while not self.stop_event.is_set():
            for char in choosen_spinner:
                message = f'{char} {self.message} ... '

                if os.name == 'nt':
                    special_print(message + ' ' * 5, with_sys = True)
                else:
                    special_print(message, end = '', flush = True)

                sleep(sleep_time)
                if self.stop_event.is_set():
                    break

    def start(self):
        """
        Starts the spinner animation.
        """

        self.spinner_thread.start()

    def stop(self):
        """
        Stops the spinner animation and clears the console.
        """

        self.stop_event.set()
        self.spinner_thread.join()

        if os.name == 'nt':
            special_print(f'~ {self.message} ... Done\n', with_sys = True)
        else:
            special_print(f'~ {self.message} ... Done\n', end='', flush=True)


class StatusWrapper:
    """
    A class for managing the status spinner alongside a block of code.
    """

    def __init__(self) -> None:
        self.is_running_spinner = False

    @contextmanager
    def status(self, message: str):
        """
        A decorator function for managing the status spinner alongside a block of code.

        :param message: The message to display alongside the spinner.
        """

        if self.is_running_spinner:
            yield
            return

        spinner = StatusSpinner(message)
        self.is_running_spinner = True
        try:
            spinner.start()
            yield
        finally:
            spinner.stop()
            self.is_running_spinner = False


@contextmanager
def dummy_cm(*args, **kwargs):
    """
    A dummy context manager that yields its arguments.
    """

    yield
    return args, kwargs


def use_context_manager(context_manager: Optional[Union[StatusWrapper, Callable]] = None,
                        **kwargs) -> Tuple[Callable, dict]:
    """
    This function facilitates the use of context managers within Python code.

    :param context_manager: Optional. A callable object representing the context manager to be used.
                            If None, a default context manager (`dummy_cm`) will be used.
    :param kwargs: Additional keyword arguments to be passed to the context manager.
    :return: A tuple containing the context manager and a dictionary of keyword arguments.
    """

    if context_manager is None:
        return dummy_cm, {}

    if isinstance(context_manager, StatusWrapper):
        return context_manager.status, kwargs

    return context_manager, kwargs


def make_bytes_human_readable(number_of_bytes: int, precision: int = 1):
    """
    Formats a byte count into a human-readable string representation.

    :param number_of_bytes: The number of bytes to format.
    :param precision: The number of decimal places to include in the formatted string. 
    :return: A human-readable string representation of the byte count.
    """

    units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    for unit in units:
        if number_of_bytes < 1024:
            return f'{number_of_bytes:.{precision}f} {unit}'
        number_of_bytes /= 1024
    return f'{number_of_bytes:.{precision}f} YB'


class Progress:
    """
    A class for tracking and displaying progress.
    """

    def __init__(self, message: str, total: int, is_download: bool = False):
        """
        Initializes the Progress object.

        :param message: A message to describe the progress being tracked.
        :param total: The total number of units to be processed.
        :param is_download: Indicates whether the progress is for a download process.
        """

        self.message = message
        self.total = total
        self.is_download = is_download

        self.finished = 0
        self.start_time = time()
        self.last_remaining_time = None

    def update(self, finished: int):
        """
        Updates the progress status.

        :param finished: The number of units processed.
        """

        if finished <= self.finished:
            return

        self.finished = finished

        is_finished = False
        if self.finished >= self.total:
            self.total = self.finished
            is_finished = True

        elapsed_time = time() - self.start_time
        progress_speed = self.finished / elapsed_time if elapsed_time > 0 else 0

        remaining = self.total - self.finished
        remaining_time = max(0, remaining / progress_speed if progress_speed > 0 else float('inf'))
        if remaining_time == 0:
            remaining_time_str = "0"
        else:
            remaining_time_str = f"{remaining_time:.1f}"\
                if remaining_time < float('inf') else "unknown"

        speed_str = "unknown"

        if progress_speed > 0:
            if not self.is_download:
                speed_str = str(progress_speed) + "/s"
            else:
                speed_str = make_bytes_human_readable(progress_speed, 0) + "/s"

        total = str(self.total)
        finished = str(self.finished)
        if self.is_download:
            total = make_bytes_human_readable(self.total)
            finished = make_bytes_human_readable(self.finished)

        progress = math.ceil((self.finished / self.total) * 30)
        progress_bar = '[' + '-' * (progress - 1) + '→' + ' ' * (30 - progress) + ']'

        status = f'{self.message} [{finished} of {total}]'+\
                 f' {progress_bar} ({speed_str} {remaining_time_str} s)'

        if is_finished:
            status += ' Done\n'

        if self.is_download:
            status = '[magenta]↓[reset] ' + status

        if os.name == 'nt':
            special_print(status + ' ' * 5, with_sys = True)
        else:
            special_print(status, end = '', flush = True)


class AnchorParser(HTMLParser):
    """
    AnchorParser is a subclass of HTMLParser used for
    extracting anchor elements (<a>) from HTML code.
    """

    def __init__(self):
        """
        Initializes the AnchorParser object.
        """

        super().__init__()
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        """
        Overrides the handle_starttag method of HTMLParser.
        This method is called whenever the parser encounters a start tag in the HTML.
        
        :param tag: The name of the tag encountered.
        :param attrs: A list of (name, value) pairs containing the attributes of the tag.
        """
        if tag == 'a':
            href = None
            for attr in attrs:
                if attr[0] == 'href':
                    href = attr[1]
                    break
            if href is not None:
                self.anchors.append(href)


def extract_anchors(html: str):
    """
    Extracts anchor elements (<a>) from the given HTML code.

    :param html: The HTML code from which anchors need to be extracted.
    :return: A list of dictionaries, where each dictionary represents
             the attributes of an anchor element.
    """

    parser = AnchorParser()
    parser.feed(html)
    return parser.anchors
