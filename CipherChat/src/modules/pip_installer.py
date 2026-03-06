"""
📦 Module for installation of pip packets

Installs a pip package if possible and otherwise a virtual Python environment with
`python -m venv <VENV_DIR>`, if Venv is not installed it is also installed with PIP
or on Windows Miniconda, Macos HomeBrew and on Linux with the packet manager, also
installs Miniconda and Homebrew if not available.
"""

import os
import sys
from typing import Tuple, Optional

try:
    from src.modules.cons import VENV_PYTHON_FILE_PATH, THIS_PYTHON, MINICONDA_WINDOWS,\
         MINICONDA_UNIX, PACKAGES, TEMP_DIR_PATH, OS, VENV_DIR_PATH, MAIN_PYTHON_FILE_PATH
    from src.modules.special import UserAgents, Linux, download_file
    from src.modules.utils import StatusWrapper, SecureDelete, use_context_manager,\
         run_command, special_print
except ImportError:
    from cons import VENV_PYTHON_FILE_PATH, THIS_PYTHON, MINICONDA_WINDOWS, MINICONDA_UNIX,\
         PACKAGES, TEMP_DIR_PATH, OS, VENV_DIR_PATH, MAIN_PYTHON_FILE_PATH
    from special import UserAgents, Linux, download_file
    from utils import StatusWrapper, SecureDelete, use_context_manager, run_command, special_print


def is_pip() -> bool:
    """
    Check if pip is available and functioning properly.

    :return: True if pip is available and functioning properly, False otherwise.
    """

    if VENV_PYTHON_FILE_PATH == THIS_PYTHON:
        return True

    command = [THIS_PYTHON, '-m', 'pip', '--version']

    is_error, _, stderr, return_code = run_command(command)

    if is_error or return_code != 0 or 'No module named pip' in stderr:
        return False

    return True


def is_anaconda() -> Tuple[int, Optional[str]]:
    """
    Check if Anaconda (or Miniconda) is installed and return its executable path if found.

    :return: True if Anaconda (or Miniconda) is found, otherwise False and path
             to the Anaconda (or Miniconda) executable if found, otherwise None.
    """

    conda_path = MINICONDA_WINDOWS if os.name == 'nt' else MINICONDA_UNIX

    if os.name == 'nt':
        windows_path = f'C:\\Users\\{str(os.getlogin())}\\miniconda3\\Scripts\\conda.exe'
        if os.path.isfile(windows_path):
            return True, windows_path

    for path in conda_path:
        if os.path.isfile(path):
            return True, path
    return False, None


IS_PIP = is_pip()
IS_ANACONDA, CONDA_FILE_PATH = is_anaconda()
IS_HOMEBREW = os.path.exists('/usr/local/Homebrew/bin/brew')


def find_python_executable() -> Optional[str]:
    """
    Find the path of the Python executable without using the current Python interpreter.
    
    :return: The path to the Python executable, or None if not found.
    """

    python_executable = None

    possible_executables = ['python3', 'python'] if os.name != 'nt' else ['python', 'python.exe']

    for path in os.environ.get('PATH', '').split(os.pathsep):
        for executable in possible_executables:
            python_candidate = os.path.join(path, executable)
            if os.path.isfile(python_candidate):
                python_executable = python_candidate
                break
        if python_executable:
            break

    return python_executable


def is_package_installed(package_name: str, python_path: str) -> bool:
    """
    Checks if the specified Python library exists in a python environment

    :param package_name: The name of the Python package to check for.
    :param python_path: The path to the Python interpreter executable.
    :return: True if the library is imported, False otherwise.
    """

    python_dir_path = os.path.basename(os.path.basename(python_path))
    package_path = os.path.join(python_dir_path, 'Lib', 'site-packages', package_name)

    return os.path.exists(package_path)


def pip_install(package_name: str, python: str = THIS_PYTHON,
                status: Optional[StatusWrapper] = None) -> bool:
    """
    This function installs a specified Python package using pip.

    :param package_name: The name of the package to be installed.
    :param python: The right Python installation
    :param status: Optional status wrapper object to provide installation progress.
    :return: True if the package was installed successfully, False otherwise.
    """

    package = PACKAGES[package_name]

    context_manager, kwargs = use_context_manager(
        status, message = '[green]Installing ' + package['name'] + ' - ' + package['description']
    )

    command = [python, '-m', 'pip', 'install', package['installation_name']]
    with context_manager(**kwargs):
        is_error, stdout, _, return_code = run_command(command)

    if isinstance(stdout, str):
        if is_error or return_code != 0 or stdout == '':
            return False
        if 'Successfully installed ' + package['installation_name'] in stdout:
            return True

    return False


def install_anaconda(user_agents: UserAgents,
                     status: Optional[StatusWrapper] = None) -> bool:
    """
    Downloads the latest Miniconda installer for Windows from the official
    Anaconda repository and installs it silently with default options.

    :param user_agents: UserAgents object containing user agents for HTTP requests.
    :param status: Optional status wrapper for displaying installation progress.
    :return: True if installation is successful, False otherwise.
    """

    if not OS == 'windows':
        raise OSError('Function `install_anaconda` should only be used on Windows')

    if not os.path.exists(TEMP_DIR_PATH):
        os.makedirs(TEMP_DIR_PATH, exist_ok = True)

    url = 'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe'
    file_path = download_file(url, TEMP_DIR_PATH, 'Miniconda',
                              'Miniconda.exe', 82000000, user_agents)

    if not isinstance(file_path, str):
        return False

    command = [file_path, '/S', '/AddToPath=1']

    context_manager, kwargs = use_context_manager(
        status, message = '[green]Automatic installation of Miniconda (that may take a while)'
    )

    with context_manager(**kwargs):
        is_error, _, stderr, return_code = run_command(command)

    with status.status('[green]Cleaning up (that may take a while)'):
        SecureDelete.directory(TEMP_DIR_PATH)

    if is_error or return_code != 0 or not isinstance(stderr, str):
        return False

    return True


def install_homebrew(user_agents: UserAgents) -> bool:
    """
    Downloads the Homebrew installation script from its official repository
    and executes it to install Homebrew package manager on macOS.

    :param user_agents: UserAgents object containing user agents for HTTP requests.
    :return: True if installation is successful, False otherwise.
    """

    if not OS == 'darwin':
        raise OSError('Function `install_homebrew` should only be used on macOS')

    if not os.path.exists(TEMP_DIR_PATH):
        os.makedirs(TEMP_DIR_PATH, exist_ok = True)

    url = 'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh'
    file_path = download_file(url, TEMP_DIR_PATH, 'Homebrew',
                              'homebrew.sh', 31000, user_agents)

    if not isinstance(file_path, str):
        return False

    command = ['sudo', '/bin/bash', '-c', file_path]
    is_error, _, stderr, return_code = run_command(command, True)

    if is_error or return_code != 0 or not isinstance(stderr, str) or stderr == '':
        return False

    return True


def install_virtualenv(user_agents: UserAgents, status: StatusWrapper) -> None:
    """
    This function installs the Virtualenv package manager in the Python environment.
    It supports installation on multiple operating systems and utilizes different
    package managers accordingly.

    :param user_agents: An object containing user agents information.
    :param status: A wrapper for managing the status of installation processes.
    :return: None
    """

    is_installed = False

    if not is_installed:
        if OS == 'windows':
            is_anaconda_installed = True
            if not IS_ANACONDA:
                is_anaconda_installed = install_anaconda(user_agents, status)

            if is_anaconda_installed:
                command = [CONDA_FILE_PATH, 'install', '-c', 'anaconda', 'virtualenv', '-y']

                context_manager, kwargs = use_context_manager(
                    status, message = '[green]Installing Virtualenv via Anaconda'
                )

                with context_manager(**kwargs):
                    is_error, stdout, _, return_code = run_command(command)

                if is_error or return_code != 0 or not isinstance(stdout, str) or stdout == '':
                    special_print('- [red] Virtualenv could not be installed with Anaconda')
                else:
                    is_installed = True

        elif OS == 'linux':
            context_manager, kwargs = use_context_manager(
                status, message = '[green]Trying to get Linux package manager'
            )
            with context_manager(**kwargs):
                package_manager = Linux.get_package_manager()

            if None in package_manager:
                update_command = input('Please enter the update command of your Packet'+
                                    ' Manager (e.g. `apt-get update; apt-get upgrade`): ')
                installation_command = input('Please enter the install command of your Packet'+
                                            ' Manager (e.g. `apt-get install`): ')
                package_manager = (installation_command, update_command)

            is_installed = Linux.install_package('python3-venv', package_manager)
        elif OS == 'darwin':
            is_homebrew_installed = True
            if not IS_HOMEBREW:
                is_homebrew_installed = install_homebrew(user_agents)

            if is_homebrew_installed:
                command = ['sudo', '/usr/local/Homebrew/bin/brew', 'install', 'pyenv-virtualenv']
                is_error, _, stderr, return_code = run_command(command, True)

                if is_error or return_code != 0 or not isinstance(stderr, str) or stderr == '':
                    special_print('- [red] Virtualenv could not be installed with Anaconda')
                else:
                    is_installed = True

    if not is_installed:
        is_installed = pip_install('venv')

    if not is_installed:
        special_print('- [red] Virtualenv could not be installed')
    else:
        special_print('- [green] Virtualenv has been installed')

def install_package(package_name: str, user_agents: UserAgents,
                    status: StatusWrapper) -> bool:
    """
    Install a Python package either globally or within a virtual environment.

    :param package_name: The name of the package to install.
    :param user_agents: An object containing user agents information.
    :param status: A wrapper for managing the status of installation processes.
    :return: A boolean indicating whether the installation was successful.
    """

    if IS_PIP:
        is_installed = pip_install(package_name, status = status)
        if is_installed:
            return True

        try:
            __import__(package_name)
        except ImportError:
            pass
        else:
            return True

    if not os.path.exists(VENV_PYTHON_FILE_PATH):
        python_path = THIS_PYTHON

        new_python_path = find_python_executable()
        if new_python_path is not None:
            python_path = new_python_path

        command = [python_path, '-m', 'venv', VENV_DIR_PATH]

        context_manager, kwargs = use_context_manager(
            status, message = '[green]Creating a virtual Python environment'
        )
        with context_manager(**kwargs):
            is_error, _, stderr, return_code = run_command(command, True)

        if is_error or 'No module named venv' in stderr\
            or return_code != 0 or not os.path.exists(VENV_DIR_PATH):
            install_virtualenv(user_agents, status)

            command = [python_path, '-m', 'venv', VENV_DIR_PATH]
            is_error, _, stderr, return_code = run_command(command, True)

            if is_error or return_code != 0 or not os.path.exists(VENV_DIR_PATH):
                is_installed = pip_install(package_name, status = status)
                if is_installed:
                    return True

                return False

    if not is_package_installed(package_name, VENV_PYTHON_FILE_PATH):
        pip_install(package_name, VENV_PYTHON_FILE_PATH, status)

    special_print('\nPlease restart CipherChat with the following command:'+
                    f' `[cyan]{VENV_PYTHON_FILE_PATH} {MAIN_PYTHON_FILE_PATH}'+
                    f' {' '.join(sys.argv)}[reset]`')
    sys.exit(0)
