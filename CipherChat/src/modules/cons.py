import os
import sys
import ssl
import platform
from typing import Final, Tuple, Optional


def get_current_dir_path() -> str:
    """
    Get the absolute path of the current directory.

    :return: The absolute path of the current directory.
    """

    current_dir_path: str = os.path.dirname(os.path.abspath(__file__))
    current_dir_path = current_dir_path.replace('//', '/')\
                       .replace('\\', '/').replace('/src/modules', '')
    current_dir_path = current_dir_path.replace('/', '\\' if os.name == 'nt' else '/')
    return current_dir_path


def get_system_information() -> Tuple[str, str]:
    """
    Function to get the correct system information
    """

    operating_system = platform.system()
    if operating_system == 'Darwin':
        operating_system = 'macOS'

    if operating_system not in ['Windows', 'macOS', 'Linux']:
        operating_system = 'Linux'

    architecture_mappings = {
        'AMD64': 'x86_64',
        'i386': 'i686'
    }

    architecture = platform.machine()
    architecture = architecture_mappings.get(architecture, 'x86_64')
    return operating_system, architecture


CURRENT_DIR_PATH: Final[str] = get_current_dir_path()
SRC_DIR_PATH: Final[str] = os.path.join(CURRENT_DIR_PATH, 'src')
ASSETS_DIR_PATH: Final[str] = os.path.join(SRC_DIR_PATH, 'assets')
DATA_DIR_PATH: Final[str] = os.path.join(SRC_DIR_PATH, 'data')
TEMPLATES_DIR_PATH: Final[str] = os.path.join(SRC_DIR_PATH, 'templates')
TEMP_DIR_PATH = os.path.join(SRC_DIR_PATH, 'tmp')

TOR_DIR_PATH = os.path.join(DATA_DIR_PATH, 'tor')
TOR_DEFAULT_BRIDGES_FILE_PATH = os.path.join(
    DATA_DIR_PATH, 'tor', 'tor', 'pluggable_transports', 'pt_config.json'
)
DEFAULT_BRIDGES_FILE_PATH = os.path.join(ASSETS_DIR_PATH, 'default_bridges.json')

CONFIG_FILE_PATH = os.path.join(DATA_DIR_PATH, 'config.json')
VENV_DIR_PATH = os.path.join(SRC_DIR_PATH, 'venv')
MAIN_PYTHON_FILE_PATH = os.path.join(SRC_DIR_PATH, 'main.py')


def get_version() -> Optional[str]:
    """
    Retrieve the version string from a file.

    :return: The version string read from the file 'version.txt'
             if it exists and can be accessed, otherwise None.
    """

    version_file_path = os.path.join(CURRENT_DIR_PATH, 'version.txt')

    version = None
    if os.path.isfile(version_file_path) and\
        os.chmod(version_file_path, os.R_OK):

        try:
            with open(version_file_path, 'r', encoding = 'utf-8') as version_file:
                version = version_file.read()
        except (FileNotFoundError, PermissionError,
                UnicodeDecodeError, OSError, IOError):
            pass

    return version


OS, ARCHITECTURE = get_system_information()
VERSION = get_version()
THIS_PYTHON = sys.executable

# main.py
PGP_KEY_SERVERS: Final[list] =\
[
    '🔐 keys.openpgp.org (Recommended)', '🍎 pgp.mit.edu', '🌟 keys.gnupg.net',
    '💼 keyserver.pgp.com', '🐧 keyserver.ubuntu.com', '📬 keys.mailvelope.com',
    '🌍 pgpkeys.eu', '🆔 pgp.id', '👾 keys.ttc.io', '🏄 pgp.surfnet.nl',
    '🛟 openpgp.circl.lu', '📂 openpgpkeyserver.com', '⚪ keyserver1.pgp.com',
    '⚪ keyserver2.pgp.com'
]

HELP_COMMANDS: Final[list] =\
[
    {
        "name": "Help",
        "arguments": ["-h", "--help"],
        "description": "Provides helpful information about all commands or specific commands",
        "short_description": "Help information and information about commands",
        "parameters": [
            {
                "name": "<command>",
                "description": "A command without `-` or `--`, e.g. `about` or `killswitch`."
            }
        ],
        "examples": [
            {
                "command": "python main.py -h",
                "description": "Returns all existing commands"
            },
            {
                "command": "python main.py -h killswitch",
                "description": "Returns all information about the `--killswitch` command"
            }
        ]
    },
    {
        "name": "Killswitch",
        "arguments": ["-k", "--killswitch"],
        "description": "Deletes all files from CipherChat or the Data Directory"+
                       " in emergency situations as an immediate off switch. Can"+
                       " also delete the recycle bin. Executed immediately after input.",
        "short_description": "Secure deletion of all information in an emergency",
        "parameters": [
            {
                "name": "all",
                "description": "All CipherChat files are deleted"
            },
            {
                "name": "notall",
                "description": "Only files in the data directory (i.e. your user data) are deleted"
            },
            {
                "name": "trash",
                "description": "All data in the recycle bin is deleted"
            },
            {
                "name": "nottrash",
                "description": "The recycle bin is not deleted"
            }
        ],
        "pairs": [
            ["all", "notall"],
            ["trash", "nottrash"]
        ],
        "examples": [
            {
                "command": "python main.py -k",
                "description": "Prompts whether all files or only the data directory"+
                               " and whether the trash can should also be deleted"
            },
            {
                "command": "python main.py -k all trash",
                "description": "Immediately deletes all data from Cipherchat and the trash can"
            },
            {
                "command": "python main.py -k notall nottrash",
                "description": "Deletes only the data directory and not"+
                        	   " the trash can or all data from CipherChat"
            }
        ]
    },
    {
        "name": "Update",
        "arguments": ["-u", "--update"],
        "description": "Can be used to update CipherChat to the latest version",
        "short_description": "Installs updates and specific versions",
        "parameters": [
            {
                "name": "<version>",
                "description": "Specifies which version to update to."
            },
            {
                "name": "nocheck",
                "description": "Deactivates the check whether the"+
                               " current version is the latest one."
            }
        ],
        "examples": [
            {
                "command": "python main.py -u",
                "description": "Updates CipherChat to the newest version"
            },
            {
                "command": "python main.py -u 1.5",
                "description": "Starts an update to version 1.5"
            }
        ]
    },
    {
        "name": "Installer",
        "arguments": ["-i", "--installer"],
        "description": "Can be used to repair the installation of CipherChat,"+
                       " as all important programs are reinstalled",
        "short_description": "To repair / reinstall required programs",
        "parameters": [
            {
                "name": "proxy",
                "description": "Use proxies to install Tor"
            },
            {
                "name": "noproxy",
                "description": "Do not use proxies to install Tor"
            },
            {
                "name": "check",
                "description": "Verify signatures from Tor"
            },
            {
                "name": "nocheck",
                "description": "No verification of Tor signatures, no installation of GnuPG"
            },
            {
                "name": "<keyserver>",
                "description": "Keyserver to be used to download keys"
            }
        ],
        "pairs": [
            ["proxy", "noproxy"],
            ["check", "nocheck"]
        ],
        "examples": [
            {
                "command": "python main.py -i",
                "description": "Starts the installer"
            },
            {
                "command": "python main.py --installer",
                "description": "Starts the installer"
            }
        ]
    },
    {
        "name": "About",
        "arguments": ["-a", "--about"],
        "description": "Displays information about CipherChat, including"+
                       " a description and instructions.",
        "short_description": "Displays information about CipherChat",
        "examples": [
            {
                "command": "python main.py -a",
                "description": "Displays information about CipherChat"
            },
            {
                "command": "python main.py --about",
                "description": "Displays information about CipherChat"
            }
        ]
    },
    {
        "name": "Version",
        "arguments": ["-v", "--version"],
        "description": "Displays the version of CipherChat",
        "short_description": "Current Version",
        "examples": [
            {
                "command": "python main.py -v",
                "description": "Displays the version of CipherChat"
            },
            {
                "command": "python main.py --version",
                "description": "Displays the version of CipherChat"
            }
        ]
    }
]

TOR_EXECUTABLE_PATH = {
    "Windows": os.path.join(DATA_DIR_PATH, "tor/tor/tor.exe")
    }.get(OS, os.path.join(DATA_DIR_PATH, "tor/tor/tor"))


# utils.py
DELETION_FILE_BYTES: Final[int] = 50000000
ENV = dict(os.environ)
ENV["LANG"] = "en_US.UTF-8"

LOGO_SMALL: Final[str]  = '''
 dP""b8 88 88""Yb 88  88 888888 88""Yb  dP""b8 88  88    db    888888 
dP   `" 88 88__dP 88  88 88__   88__dP dP   `" 88  88   dPYb     88   
Yb      88 88"""  888888 88""   88"Yb  Yb      888888  dP__Yb    88   
 YboodP 88 88     88  88 888888 88  Yb  YboodP 88  88 dP""""Yb   88   

-~-    Programmed by TN3W - https://github.com/tn3w/CipherChat    -~-
'''
LOGO_BIG: Final[str] = '''
             @@@@@            
       @@@@@@@@@@@@@@@@@      
    @@@@@@@@@@@@@@@   @@@@@   
  @@@@@@@@@@@@@@ @@@@@@  @@@@ 
 @@@@@@@@@@@@@@@@@@  @@@@  @@@   dP""b8 88 88""Yb 88  88 888888 88""Yb  dP""b8 88  88    db    888888 
 @@@@@@@@@@@@@@@ @@@@  @@@ @@@  dP   `" 88 88__dP 88  88 88__   88__dP dP   `" 88  88   dPYb     88   
@@@@@@@@@@@@@@@@   @@  @@@  @@@ Yb      88 88"""  888888 88""   88"Yb  Yb      888888  dP__Yb    88   
 @@@@@@@@@@@@@@@ @@@@  @@@ @@@   YboodP 88 88     88  88 888888 88  Yb  YboodP 88  88 dP""""Yb   88  
 @@@@@@@@@@@@@@@@@@  @@@@ @@@@  -~-    Programmed by TN3W - https://github.com/tn3w/CipherChat    -~-
  @@@@@@@@@@@@@@@@@@@@@  @@@  
    @@@@@@@@@@@@@@@   @@@@@   
       @@@@@@@@@@@@@@@@@      
'''

PASSWORD_REGEX: Final[list] = [r'[A-Z]', r'[a-z]', r'[\d]',
                               r'[!@#$%^&*()_+{}\[\]:;<>,.?~\\]']


# special.py
DUMMY_CRAWLER_USER_AGENT_HEADER: dict = {"User-Agent":  "Mozilla/5.0 (compatible;"+
                                         " DummyCrawl/6.9; +http://www.dummy-crawler.io/)"}
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '+\
                     '(KHTML, like Gecko) Version/16.6 Safari/605.1.1'

PACKAGE_MANAGERS = [
    {
        "version_command": "apt-get --version",
        "installation_command": "apt-get install",
        "update_command": "apt-get update; apt-get upgrade"
    },
    {
        "version_command": "dnf --version",
        "installation_command": "dnf install",
        "update_command": "dnf upgrade"
    },
    {
        "version_command": "yum --version",
        "installation_command": "yum install",
        "update_command": "yum update"
    },
    {
        "version_command": "pacman --version",
        "installation_command": "pacman -S",
        "update_command": "pacman -Syu"
    },
    {
        "version_command": "zypper --version",
        "installation_command": "zypper install",
        "update_command": "zypper update"
    },
    {
        "version_command": "emerge --version",
        "installation_command": "emerge",
        "update_command": "emerge --sync"
    },
    {
        "version_command": "eopkg --version",
        "installation_command": "eopkg install",
        "update_command": "eopkg up"
    }
]

PROXY_SSL_CONTEXT = ssl.create_default_context()
PROXY_SSL_CONTEXT.check_hostname = False
PROXY_SSL_CONTEXT.verify_mode = ssl.CERT_NONE # allows self signed certificates
PROXY_SSL_CONTEXT.load_default_certs()


# installation.py
GNUPG_EXECUTABLE_PATH = {
    "Windows": "C:\\Program Files (x86)\\GnuPG\\bin\\gpg.exe",
    "macOS": "/usr/local/bin/gpg"
}.get(OS, "/usr/bin/gpg")

BRIDGE_URLS = {
    "main": "https://raw.githubusercontent.com/scriptzteam/"+
            "Tor-Bridges-Collector/main/bridges-",
    "backup": "https://tor-bridges-collector.0xc0d3.xyz/"+
              "Tor-Bridges-Collector-main/bridges-"
}

DEFAULT_CONFIGURATION = {
    'bridges': {
        'use': True,
        'type': 'obfs4',
        'buildin': False,
        'bridgedb': True
    },
    'persistent_storage': {
        'use': False,
        'store_user_data': False
    },
    'installation': {
        'proxies': True,
        'signature_verification': True,
        'keyserver': 'keys.openpgp.org'
    },
    'updates': {
        'check': False,
        'auto': False
    }
}

TOR_FINGERPRINT = "0xEF6E286DDA85EA2A4BA7DE684E2C6E8793298290"


# pip_installer.py
PACKAGES = {
    "venv": {
        "installation_name": "virtualenv",
        "name": "Venv",
        "description": "Isolationg Python environments"
    },
    "PIL": {
        "installation_name": "pillow",
        "name": "Pillow",
        "description": "Python Imaging Library"
    }
}

VENV_PYTHON_FILE_PATH = {"windows": os.path.join(VENV_DIR_PATH, 'Scripts', 'python.exe')}\
                        .get(OS, os.path.join(VENV_DIR_PATH, 'bin', 'python'))

MINICONDA_FILE_PATH = f'C:\\Users\\{str(os.getlogin())}\\miniconda3\\Scripts\\conda.exe'
MINICONDA_WINDOWS = [
    "C:\\ProgramData\\Miniconda3\\Scripts\\conda.exe",
    "C:\\Program Files\\Miniconda3\\Scripts\\conda.exe",
    "C:\\ProgramData\\Anaconda3\\Scripts\\conda.exe",
    "C:\\Program Files\\Anaconda3\\Scripts\\conda.exe"
]
MINICONDA_UNIX = [
    "/opt/miniconda3/bin/conda",
    "/usr/local/miniconda3/bin/conda",
    "/opt/anaconda3/bin/conda",
    "/usr/local/anaconda3/bin/conda"
]
