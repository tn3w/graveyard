import os
import sys
import re
import shutil
import json
import base64
import subprocess
from io import BytesIO
from time import sleep
from copy import deepcopy
from typing import Optional, Tuple
from html.parser import HTMLParser
from PIL import Image

try:
    from src.modules.cons import DEFAULT_CONFIGURATION, DATA_DIR_PATH, CONFIG_FILE_PATH,\
         GNUPG_EXECUTABLE_PATH, OS, TEMP_DIR_PATH, TOR_EXECUTABLE_PATH, ARCHITECTURE,\
         TOR_FINGERPRINT, TOR_DIR_PATH, BRIDGE_URLS, PGP_KEY_SERVERS
    from src.modules.utils import StatusWrapper, SecureDelete, JSON, clear_console, special_print,\
         check_permissions, selection, pwd_input, get_password_strength, extract_anchors,\
         extract_tar, get_console_size, run_command, is_character_supported
    from src.modules.special import Proxies, UserAgents, Linux, TorBridges, Data,\
         download_file, macos_get_installer_and_volume_path, request, is_password_pwned,\
         parse_pgp_import_output, parse_pgp_verify_output, is_key_imported
    from src.modules.cryptographic import Hashing, PasswordSigning
except ImportError:
    from cons import DEFAULT_CONFIGURATION, DATA_DIR_PATH, CONFIG_FILE_PATH, GNUPG_EXECUTABLE_PATH,\
         OS, TEMP_DIR_PATH, TOR_EXECUTABLE_PATH, ARCHITECTURE, TOR_FINGERPRINT, TOR_DIR_PATH,\
         BRIDGE_URLS, PGP_KEY_SERVERS
    from utils import StatusWrapper, SecureDelete, JSON, clear_console, special_print,\
         check_permissions, selection, pwd_input, get_password_strength, extract_anchors,\
         extract_tar, get_console_size, run_command, is_character_supported
    from special import Proxies, UserAgents, Linux, TorBridges, Data,\
         download_file, macos_get_installer_and_volume_path, request, is_password_pwned,\
         parse_pgp_import_output, parse_pgp_verify_output, is_key_imported
    from cryptographic import Hashing, PasswordSigning


def get_gnupg_path() -> Optional[str]:
    """
    Retrieves the path to the GnuPG executable.

    :return: The path to the GnuPG executable if found, otherwise None.
    """

    command = {"Windows": "where gpg"}.get(OS, "which gpg")
    try:
        result = subprocess.run(command, check=True, shell=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        gnupg_path = result.stdout.strip()
        if os.path.isfile(gnupg_path):
            return gnupg_path
    except subprocess.CalledProcessError:
        pass
    return None


def image_bytes_to_ascii(image_bytes: bytes) -> str:
    """
    Convert the input image represented as bytes to ASCII art.

    :param image_bytes: Bytes representing the input image.
    :return: ASCII representation of the input image.
    """

    img = Image.open(BytesIO(image_bytes))

    ascii_chars = '@%#*+=-:. '

    width, height = img.size
    aspect_ratio = height / width
    _, new_width = get_console_size()

    new_width = min(new_width, 112) - 2

    new_height = int(aspect_ratio * new_width * 0.55)

    img = img.resize((new_width, new_height))
    img = img.convert('L')

    pixels = img.getdata()

    ascii_str = ''.join([ascii_chars[min(pixel // 25, len(ascii_chars) - 1)] for pixel in pixels])
    ascii_str_len = len(ascii_str)
    ascii_img = '┌' + '─' * (new_width) + '┐\n'

    for i in range(0, ascii_str_len, new_width):
        ascii_img += '│' + ascii_str[i:i + new_width] + '│\n'

    ascii_img += '└' + '─' * (new_width) + '┘'

    return ascii_img


class BridgeDBImageParser(HTMLParser):
    """
    A parser for extracting captcha image and form information from BridgeDB HTML content.
    """

    def __init__(self):
        """
        Initialize the BridgeDBParser instance.
        """
        super().__init__()

        self.captcha_image_src = None
        self.captcha_challenge_value = None

        self.in_captcha_image = False
        self.in_captcha_form = False

    def handle_starttag(self, tag, attrs):
        """
        Handle start tags encountered during HTML parsing.

        :param tag: The name of the HTML tag.
        :param attrs: A list of (name, value) pairs containing the attributes of the tag.
        """
        if tag == 'div':
            for attr, value in attrs:
                if value == 'bridgedb-captcha-container':
                    self.in_captcha_image = True

        if tag == 'form':
            self.in_captcha_form = True

        if self.in_captcha_image and tag == 'img':
            for attr, value in attrs:
                if attr == 'src':
                    self.captcha_image_src = value

        elif self.in_captcha_form and tag == 'input':
            for attr, value in attrs:
                if attr == 'name' and value == 'captcha_challenge_field':
                    for attr, value in attrs:
                        if attr == 'value':
                            self.captcha_challenge_value = value


def bridgedb_extract_captcha(content: str) -> Optional[Tuple[bytes, str]]:
    """
    Extract the captcha image source from BridgeDB HTML content.

    :param content: The HTML content of the BridgeDB page.
    :return: The bytes of the captcha image and the captcha challenge value.
    """

    parser = BridgeDBImageParser()
    parser.feed(content)

    if None in [parser.captcha_image_src, parser.captcha_challenge_value]:
        return None

    captcha_image_base64 = parser.captcha_image_src.split("data:image/jpeg;base64,")[1]
    captcha_image_data: bytes = base64.b64decode(captcha_image_base64)

    return (captcha_image_data, parser.captcha_challenge_value)


class BridgeDBExtractParser(HTMLParser):
    """
    Parses HTML content from the BridgeDB extraction page to extract bridge lines.
    """

    def __init__(self):
        """
        Initialize the BridgeDBExtractParser instance.
        """

        super().__init__()
        self.bridge_lines = []
        self.inside_bridgelines = False

    def handle_starttag(self, tag: str, attrs: list):
        """
        Handle start tags encountered during HTML parsing.

        :param tag: The name of the tag encountered.
        :param attrs: A list of (name, value) pairs containing the attributes found inside the tag.
        """

        if tag == 'div':
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'bridgelines':
                    self.inside_bridgelines = True

    def handle_data(self, data: str):
        """
        Handle data encountered during HTML parsing.

        :param data: The data enclosed within tags.
        """

        if self.inside_bridgelines:
            self.bridge_lines.append(data.strip())

    def handle_endtag(self, tag: str):
        """
        Handle end tags encountered during HTML parsing.

        :param tag: The name of the tag encountered.
        """

        if tag == 'div':
            self.inside_bridgelines = False


def bridgedb_extract_bridges(content: str) -> Optional[list]:
    """
    Extracts bridge lines from the HTML content obtained from the BridgeDB extraction page.

    :param content: The HTML content obtained from the BridgeDB extraction page.
    :return: A list of extracted bridge lines.
    """

    parser = BridgeDBExtractParser()
    parser.feed(content)

    bridge_lines = parser.bridge_lines
    if len(bridge_lines) == 0:
        return None

    bridges = [bridge.strip() for bridge in bridge_lines if bridge.strip()]
    return bridges


def set_configuration(status: StatusWrapper) -> dict:
    """
    Set the system configuration based on user input.
    This function guides the user through an interactive process to set various configuration
    options for the system. The user is prompted to specify preferences for Tor Bridges usage,
    persistent storage, installation settings, and updates. The configuration is then saved to a
    file for future reference.

    :param status: An object used for displaying status messages during the configuration process.

    :return: A dictionary containing the configured settings for the system.
    """

    configuration = DEFAULT_CONFIGURATION

    text_until_now = ''

    def print_until_now():
        clear_console()
        special_print(text_until_now)

    while True:
        text_until_now = '== [green]Settings[reset] ==\n\n~ Bridges:'
        print_until_now()

        use_bridges_inp = input('Do you want to use Tor Bridges (Recommended'+
                            ' in Censored Countries)? [y / n] ')
        use_bridges = not use_bridges_inp.lower().startswith('n')

        text_until_now += '\nUse Tor Bridges: [cyan]' + ('yes' if use_bridges else 'no') + '[reset]'

        configuration['bridges']['use'] = use_bridges
        if use_bridges:
            bridge_types = ['🔒 obfs4 (Recommended)', '🍦 vanilla', '🌐 webtunnel',
                            '⛄ snowflake (only buildin)', '🌀 meek_lite (only buildin)']

            selected_bridge_type = selection(bridge_types, 'bridge type', text_until_now)
            bridge_type = selected_bridge_type.replace(' (only buildin)', '')\
                            .replace(' (Recommended)', '')

            text_until_now += f'\nSelected bridge type: [cyan]{bridge_type}[reset]'
            print_until_now()
            print()

            configuration['bridges']['type'] = bridge_type[2:]

            if bridge_type[2:] in ['snowflake', 'meek_lite']:
                use_build_in = True
            else:
                use_build_in_inp = input('Use buildin bridges (Not Recommended)? [y / n]: ')
                use_build_in = use_build_in_inp.lower().startswith('y')

                text_until_now += '\nUse Build-in Bridges: [cyan]' +\
                                    ('yes' if use_build_in else 'no') + '[reset]'
                print_until_now()

            configuration['bridges']['buildin'] = use_build_in

            if not use_build_in:
                print()
                use_bridgedb_inp = input('Use BridgeDB to get Bridges (Recommended)? [y / n]: ')
                use_bridgedb = not use_bridgedb_inp.lower().startswith('n')

                text_until_now += '\nUse BridgeDB: [cyan]' +\
                                    ('yes' if use_bridgedb else 'no') + '[reset]'
                print_until_now()

                configuration['bridges']['bridgedb'] = use_bridgedb

        print()
        do_continue = input('Is everything correct? [Enter or no] ')
        if not do_continue.lower().startswith('n'):
            break

    while True:
        text_until_now = '== [green]Settings[reset] ==\n\n- Bridges: '+\
                         '[green]Done.[reset]\n~ Persistent Storage:'
        print_until_now()

        use_persistent_storage_inp = input('Would you like to use Persistent'+
                                           ' Storage? [y / n]: ')
        use_persistent_storage = use_persistent_storage_inp.lower().startswith('y')

        text_until_now += '\nUse Persistent Storage: [cyan]' +\
                          ('yes' if use_persistent_storage else 'no') + '[reset]'
        print_until_now()
        print()

        configuration['persistent_storage']['use'] = use_persistent_storage

        if use_persistent_storage:
            store_user_data_inp = input('Do you also want to save user data '+
                                        '(such as passwords) [y / n]: ')
            store_user_data = store_user_data_inp.lower().startswith('y')

            text_until_now += '\nStore User Data: [cyan]' +\
                            ('yes' if store_user_data else 'no') + '[reset]'

            configuration['persistent_storage']['store_user_data'] = store_user_data

            persistent_storage_pwd = None
            while persistent_storage_pwd is None:
                print_until_now()
                print()

                persistent_storage_pwd_inp = pwd_input('Enter a secure Persistent'+
                                                       ' Storage password: ')
                password_strength = get_password_strength(persistent_storage_pwd_inp)

                if password_strength < 80:
                    special_print('- [red][Error] Your password is not secure enough.')
                    input_continue = input('Still use it? [y / n] ')

                    if not input_continue.lower().startswith('y'):
                        continue
                else:
                    password_strength_color = 'green' if password_strength > 95 else\
                                            'yellow' if password_strength > 90 else 'red'
                    special_print(f'- Password Strength: [{password_strength_color}]'+
                                f'{password_strength} / 100[reset]')

                with status.status('[green]Checking your password for data leaks'):
                    is_pwned = is_password_pwned(persistent_storage_pwd_inp)

                print()
                if is_pwned:
                    special_print('- [red][Error] Your password is included in data leaks.')
                    input_continue = input('Still use it? [y / n] ')

                    if not input_continue.lower().startswith('y'):
                        continue

                persistent_pwd_check_inp = pwd_input('Please enter your password again: ')
                if not persistent_pwd_check_inp == persistent_storage_pwd_inp:
                    special_print('- [red][Error] The passwords do not match.')
                    input('Enter: ')
                    continue

                text_until_now += '\nPersistent password: [cyan]set[reset]'
                print_until_now()
                print()

                persistent_storage_pwd = persistent_storage_pwd_inp
                break

            configuration['persistent_storage']['password'] = persistent_storage_pwd

        do_continue = input('Is everything correct? [Enter or no] ')
        if not do_continue.lower().startswith('n'):
            break

    while True:
        text_until_now = '== [green]Settings[reset] ==\n\n- Bridges: '+\
                         '[green]Done.[reset]\n- Persistent Storage: '+\
                         '[green]Done.[reset]\n~ Installation:'
        print_until_now()

        use_proxies_inp = input('Should connections always be established'+
                                ' behind a proxy (Recommended)? [y / n] ')
        use_proxies = not use_proxies_inp.lower().startswith('n')

        text_until_now += '\nUse Proxies: [cyan]' +\
                          ('yes' if use_proxies else 'no') + '[reset]'
        print_until_now()
        print()

        configuration['installation']['proxies'] = use_proxies

        validate_signatures_inp = input('Do you want signatures to be verified'+
                                        ' (Recommended)? [y / n] ')
        validate_signatures = not validate_signatures_inp.lower().startswith('n')

        text_until_now += '\nValidate Signatures: [cyan]' +\
                          ('yes' if validate_signatures else 'no') + '[reset]'
        print_until_now()
        print()

        configuration['installation']['signature_verification'] = validate_signatures

        if validate_signatures:
            selected_key_server = selection(
                PGP_KEY_SERVERS + ["✒️ Enter your own"], 'key server',
                text_until_now, max_display = 5
            )
            key_server = selected_key_server.replace(' (Recommended)', '')

            if 'Enter your own' in key_server:
                key_server = input('Enter a PGP keyserver: ')

            text_until_now += f'\nSelected key server: [cyan]{key_server}[reset]'
            print_until_now()
            print()

            configuration['installation']['keyserver'] = key_server[2:]

        do_continue = input('Is everything correct? [Enter or no] ')
        if not do_continue.lower().startswith('n'):
            break

    while True:
        text_until_now = '== [green]Settings[reset] ==\n\n- Bridges: '+\
                         '[green]Done.[reset]\n- Persistent Storage: '+\
                         '[green]Done.[reset]\n- Installation: '+\
                         '[green]Done.[reset]\n~ Updates:'
        print_until_now()

        check_updates_inp = input('Do you want to check for updates automatically'+
                                  ' at every startup? [y / n] ')
        check_updates = not check_updates_inp.lower().startswith('n')

        text_until_now += '\nCheck for updates: [cyan]' +\
                          ('yes' if check_updates else 'no') + '[reset]'
        print_until_now()
        print()

        configuration['updates']['check'] = check_updates

        if check_updates:
            auto_install_inp = input('Should updates be installed automatically? [y / n] ')
            auto_install = not auto_install_inp.lower().startswith('n')

            text_until_now += '\nAutomatic installation: [cyan]' +\
                            ('yes' if auto_install else 'no') + '[reset]'
            print_until_now()
            print()

            configuration['updates']['auto'] = auto_install

        do_continue = input('Is everything correct? [Enter or no] ')
        if not do_continue.lower().startswith('n'):
            break

    text_until_now = '== [green]Settings[reset] ==\n\n- Bridges: '+\
                     '[green]Done.[reset]\n- Persistent Storage: '+\
                     '[green]Done.[reset]\n- Installation: '+\
                     '[green]Done.[reset]\n~ Updates: [green]Done.[reset]'
    print_until_now()

    save_config = deepcopy(configuration)
    if 'password' in configuration['persistent_storage']:
        hashed_password = Hashing().hash(configuration['persistent_storage']['password'])
        configuration['persistent_storage']['hashed_password'] = hashed_password

        pwdsign = PasswordSigning(configuration['persistent_storage']['password'])

        del configuration['persistent_storage']['password']

        configuration_text = json.dumps(configuration)
        configuration['signature'] = pwdsign.sign(configuration_text)

    if not os.path.exists(DATA_DIR_PATH):
        os.makedirs(DATA_DIR_PATH)

    JSON.dump(configuration, CONFIG_FILE_PATH)

    return save_config


def get_configuration(status: StatusWrapper, set_conf: bool = True) -> Optional[dict]:
    """
    Retrieve the system configuration.
    This function loads the configuration settings from a file.
    If no configuration is found, it invokes the set_configuration
    function to prompt the user for new settings.

    :param status: An object used for displaying status messages during the configuration process.
    :return: A dictionary containing the configuration settings for the system.
    """

    if not os.path.exists(CONFIG_FILE_PATH):
        if not set_conf:
            return None
        configuration = set_configuration(status)
    else:
        configuration = JSON.load(CONFIG_FILE_PATH, None)
        if configuration is None:
            configuration = DEFAULT_CONFIGURATION

        if configuration['persistent_storage']['use'] and set_conf:
            if not 'hashed_password' in configuration['persistent_storage']:
                configuration['persistent_storage']['use'] = False
            else:
                save_config = deepcopy(configuration)

                hashed_password = configuration['persistent_storage']['hashed_password']
                del configuration['persistent_storage']['hashed_password']

                while True:
                    clear_console()
                    special_print('== [green]Persistent Storage[reset] ==\n')
                    persistent_storage_pwd_inp = pwd_input('Enter your Persistent'+
                                                           ' Storage password: ')

                    if Hashing().compare(persistent_storage_pwd_inp, hashed_password):
                        configuration['persistent_storage']['password'] = persistent_storage_pwd_inp
                        break

                    special_print('- [red][Error] The passwords do not match.')
                    input('Enter: ')

                pwdsign = PasswordSigning(configuration['persistent_storage']['password'])

                is_signature_invalid = False

                signature = save_config.get('signature')
                if signature is None:
                    is_signature_invalid = True
                else:
                    del save_config['signature']
                    configuration_text = json.dumps(save_config)

                    is_signature_invalid = not pwdsign.compare(configuration_text, signature)

                if is_signature_invalid:
                    if is_character_supported('🚩'):
                        special_print('\n- [red]🚩 The configuration has been changed because the'+
                                      ' signature is not correct, it could have been compromised')
                    else:
                        special_print('\n- [red]The configuration has been changed because the'+
                                      ' signature is not correct, it could have been compromised')

                    do_continue_inp = input('Continue anyway? [y / n] ')
                    if not do_continue_inp.lower().startswith('y'):
                        sys.exit(1)

                    sign_new_config_inp = input('Would you like to sign the new'+
                                                ' configuration? [y / n] ')
                    if sign_new_config_inp.lower().startswith('y'):
                        configuration_text = json.dumps(save_config)
                        save_config['signature'] = pwdsign.sign(configuration_text)

                        JSON.dump(save_config, CONFIG_FILE_PATH)

    return configuration


def gnupg_installer(required_install: bool = False,
                    user_agents: Optional[UserAgents] = None,
                    proxies: Optional[Proxies] = None,
                    status: Optional[StatusWrapper] = None) -> Tuple[str, str]:
    """
    This function checks for the presence of GnuPG, installs it if required,
    and returns the status and path of the executable.

    :param required_install: Flag indicating whether GnuPG installation is required.
    :param user_agents: User agents for HTTP requests.
    :param proxies: Proxies for HTTP requests.
    :param status: Status wrapper for displaying installation progress.
    :return: A tuple containing the status of GnuPG ('found', 'installed', 'error')
             and the path to the executable.
    """

    gnupg_status = 'found'
    gnupg_path = GNUPG_EXECUTABLE_PATH
    if not os.path.isfile(gnupg_path) or required_install:
        found_gnupg = False

        if not required_install:
            with status.status('[green]Trying to find GnuPG'):
                _gnupg_path = get_gnupg_path()
                if isinstance(_gnupg_path, str):
                    if os.path.isfile(_gnupg_path):
                        gnupg_path = _gnupg_path
                        found_gnupg = True

        if not found_gnupg:
            if not required_install:
                special_print('- [red]GnuPG not found')

            if OS == 'Linux':
                with status.status('[green]Trying to get Linux package manager'):
                    package_manager = Linux.get_package_manager()

                if None in package_manager:
                    update_command = input('Please enter the update command of your Packet'+
                                           ' Manager (e.g. `apt-get update; apt-get upgrade`): ')
                    installation_command = input('Please enter the install command of your Packet'+
                                                 ' Manager (e.g. `apt-get install`): ')
                    package_manager = (installation_command, update_command)

                is_installed = Linux.install_package("gpg", package_manager)

                if not is_installed:
                    special_print('~ [red]Installing the `gpg` package... Failure')
                else:
                    special_print('~ [green]Installing the `gpg` package... Done')

                if not is_installed:
                    installation_command, update_command = package_manager
                    manual_command = 'sudo ' + update_command + '; sudo' +\
                                     installation_command + ' gpg -y'

                    special_print('\nManual installation of gpg: Please open'+\
                                  ' a `[cyan]new console[reset]` and execute the'+\
                                  f' command `[cyan]{manual_command}[reset]`. ')

                    error_counter = 0
                    while True:
                        if error_counter != 0:
                            special_print(f'[red] Error x{str(error_counter)}: gpg'+
                                          ' has not yet been installed, try the command again')
                        else:
                            print()
                        input('Done? Enter: ')

                        _gnupg_path = get_gnupg_path()
                        if isinstance(_gnupg_path, str):
                            if os.path.isfile(_gnupg_path):
                                gnupg_path = _gnupg_path
                                break
                        error_counter += 1

                gnupg_status = 'installed'
            else:
                url = {"Windows": "https://gnupg.org/download/"}.get(OS, "https://gpgtools.org/")
                content = None

                if proxies is not None:
                    proxies.update_proxies(status, check = True)

                with status.status('[green]Getting the GnuPG download link'):
                    content = request(url, user_agents = user_agents,
                                      proxies = proxies, status = status)

                download_url = None

                if content is not None:
                    anchors = extract_anchors(content)

                    for anchor in anchors:
                        if ("/ftp/gcrypt/binary/gnupg-w32-" in anchor and ".exe" in anchor\
                            and not ".sig" in anchor and OS == "Windows"):
                            download_url = "https://gnupg.org" + anchor
                            break
                        if ("https://releases.gpgtools.com/GPG_Suite-" in anchor\
                            and ".dmg" in anchor and not ".sig" in anchor and OS == "macOS"):
                            download_url = anchor
                            break

                if download_url is None:
                    download_url = input('Please enter the download link of GnuPG software,'+
                                         ' you can find it by searching for GnuPG software'+
                                         ' for your current operating system: ')

                if not os.path.isdir(TEMP_DIR_PATH):
                    os.mkdir(TEMP_DIR_PATH)

                gnupg_file_path = download_file(download_url, TEMP_DIR_PATH, 'GnuPG', None,
                                                5600000, user_agents, proxies, status)

                if isinstance(gnupg_file_path, int):
                    special_print(f'- [red]Download Error: An error code `{int(gnupg_file_path)}`'+
                                  ' was received when downloading the file, install GnuPG'+
                                  f' yourself at `{url}`.')
                    input('Continue: ')
                    gnupg_status = 'error'
                else:
                    if not check_permissions(gnupg_file_path, 'x'):
                        special_print('- [red]Permission Error: GnuPG couldn`t install due'+
                                      ' to insufficient program rights, install GnuPG'+
                                      f' yourself at {url}.')
                        input('Continue: ')

                        gnupg_status = 'error'
                    else:
                        if OS == 'Windows':
                            command = [gnupg_file_path]
                        else:
                            mount_command = ['hdiutil', 'attach', gnupg_file_path]
                            subprocess.run(mount_command, check = True)

                            installer_path, volume_path = macos_get_installer_and_volume_path()
                            command = ['open', installer_path]

                        with status.status('[green]GnuPG installation wizard started'+
                                           ', waiting for completion'):
                            is_error, _, stderr, return_code = run_command(command, as_admin = True)

                            if OS == 'Windows':
                                while True:
                                    try:
                                        os.remove(gnupg_file_path)
                                    except PermissionError:
                                        sleep(0.5)
                                    else:
                                        break

                        if is_error:
                            special_print(f'- [red]Error opening GnuPG: {stderr}')
                            gnupg_status = 'error'

                        if OS == 'macOS':
                            unmount_command = ['hdiutil', 'detach', volume_path]
                            subprocess.run(unmount_command, check = True)

                        if return_code == 0 and not gnupg_status == 'error':
                            special_print('~ [green]GnuPG has been installed')
                            gnupg_status = 'installed'
                        else:
                            special_print('- [red]The GnuPG installation'+
                                          ' does not seem to have been successful. If errors'+
                                          f' occur, install GnuPG yourself at `{url}`\nExit Code:'+
                                          f' {return_code}; Error output: {stderr}')

                            input('Continue: ')
                            gnupg_status = 'error'

                with status.status('[green]Cleaning up (that may take a while)'):
                    SecureDelete.directory(TEMP_DIR_PATH)

            if gnupg_status != 'error':
                _gnupg_path = get_gnupg_path()

                found_gnupg = False
                if os.path.isfile(GNUPG_EXECUTABLE_PATH):
                    gnupg_path = GNUPG_EXECUTABLE_PATH
                    found_gnupg = True
                elif isinstance(_gnupg_path, str):
                    if os.path.isfile(_gnupg_path):
                        gnupg_path = _gnupg_path
                        found_gnupg = True

                if not found_gnupg:
                    special_print('[red]GnuPG could not be found despite installation')
                    input('Continue: ')
                    gnupg_status = 'error'

    return gnupg_status, gnupg_path


def tor_installer(required_install: bool = False, verify_signature: bool = True,
                  pgp_key_server: str = "keys.openpgp.org",
                  user_agents: Optional[UserAgents] = None,
                  proxies: Optional[Proxies] = None,
                  status: Optional[StatusWrapper] = None) -> str:
    """
    This function checks for the presence of Tor, installs it if required, and returns the status.

    :param required_install: Flag indicating whether GnuPG installation is required.
    :param verify_signature: Flag indicating whether signatures should be checked.
    :param user_agents: User agents for HTTP requests.
    :param proxies: Proxies for HTTP requests.
    :param status: Status wrapper for displaying installation progress.
    :return: The status of Tor installation ('found', 'installed', 'error').
    """

    if os.path.isfile(TOR_EXECUTABLE_PATH) and not required_install:
        return

    clear_console()
    title = {False: 'Installation', True: 'Repair'}.get(required_install)
    special_print(f'== [green]{title}[reset] ==')

    if verify_signature:
        print('\nGnuPG:')
        gnupg_status, gnupg_path = gnupg_installer(required_install, user_agents, proxies, status)

        clear_console()
        special_print(f'== [green]{title}[reset] ==')

        gnupg_text = {'found': '[green]Found on device',
                      'installed': '[green]Newly installed',
                      'error': '[red]Error during installation'}

        special_print('\nGnuPG: ' + gnupg_text.get(gnupg_status))
    else:
        print()

    print('Tor Expert Bundle:')

    tor_status = 'found'
    if not required_install:
        special_print('- [red]Tor not found')

    url = 'https://www.torproject.org/download/tor/'
    content = None

    if proxies is not None:
        proxies.update_proxies(status, check = True)

    with status.status('[green]Getting the Tor download link'):
        content = request(url, user_agents = user_agents,
                          proxies = proxies, status = status)

    download_url = None
    signature_url = None

    if content is not None:
        anchors = extract_anchors(content)

        for anchor in anchors:
            if "archive.torproject.org/tor-package-archive/torbrowser" in anchor:
                if OS.lower() in anchor and "tor-expert-bundle" in anchor\
                    and ARCHITECTURE.lower() in anchor:
                    if anchor.endswith(".asc"):
                        signature_url = anchor
                    else:
                        download_url = anchor

                    if not None in [signature_url, download_url]:
                        break

    is_invalid_download_url = False
    is_invalid_signature = not verify_signature

    tor_bundle_file_path = None
    tor_bundle_signature_file_path = None
    while True:
        if download_url is None or is_invalid_download_url:
            print('\nExample: `https://archive.torproject.org/'+
                  'tor-package-archive/torbrowser/VERSION/tor-'+
                  'expert-bundle-OS-ARCHITECTURE-VERSION.tar.gz`')
            download_url = input('Please enter the download link for your system'+
                                 f' `{OS}` under your architecture `{ARCHITECTURE}`'+
                                 f'in the section `Tor Expert Bundle` under the URL `{url}`.')
            if not download_url.startswith(('https://', 'http://')):
                download_url = 'https://' + download_url

        is_signature_url_guessed = False
        if signature_url is None:
            signature_url = download_url + '.asc'
            is_signature_url_guessed = True

        if not os.path.isdir(TEMP_DIR_PATH):
            os.mkdir(TEMP_DIR_PATH)

        tor_bundle_file_path = download_file(
            download_url, TEMP_DIR_PATH, 'Tor', default_length = 22000000,
            user_agents = user_agents, proxies = proxies, status = status
        )

        if verify_signature:
            tor_bundle_signature_file_path = download_file(
                signature_url, TEMP_DIR_PATH, 'Tor Signature', default_length = 1000,
                user_agents = user_agents, proxies = proxies, status = status
            )

        if not isinstance(tor_bundle_file_path, str):
            special_print('- [red]Download Error: Tor could not be downloaded,'+
                          f' error code: `{tor_bundle_file_path}`')
            is_invalid_download_url = True
            continue

        if verify_signature:
            if not isinstance(tor_bundle_signature_file_path, str):
                if is_signature_url_guessed:
                    signature_url = input('Please enter the link for the SIGNATURE'+
                                          f' for your system `{OS}` under your architecture'+
                                          f' `{ARCHITECTURE}` in the section `Tor Expert'+
                                          f' Bundle` under the URL `{url}`.')
                    if not signature_url.startswith(('https://', 'http://')):
                        signature_url = 'https://' + signature_url

                    tor_bundle_signature_file_path = download_file(
                        signature_url, TEMP_DIR_PATH, 'Tor Signature', default_length = 1000,
                        user_agents = user_agents, proxies = proxies, status = status
                    )

                    if not isinstance(tor_bundle_signature_file_path, int):
                        break

                special_print('- [red]Download Error: Signature could not be downloaded,'+
                              f' error code: `{tor_bundle_file_path}`')
                continue_without_signature = input('Would you like to continue without a'+
                                                   ' valid signature? [y / n] ')
                if continue_without_signature.lower().startswith('y'):
                    is_invalid_signature = True
                    break
                continue
        break

    if tor_bundle_signature_file_path is None and not is_invalid_signature:
        special_print('- [red]Download Error: Signature could not be downloaded.')
        continue_without_signature = input('Would you like to continue without a'+
                                           ' valid signature? [y / n] ')
        if continue_without_signature.lower().startswith('y'):
            is_invalid_signature = True

    if tor_bundle_file_path is None or\
        (tor_bundle_signature_file_path is None and not is_invalid_signature):
        special_print('- [red] Tor could not be downloaded')
        tor_status = 'error'
    elif not os.path.isfile(tor_bundle_file_path) or\
        (not os.path.isfile(tor_bundle_signature_file_path) and not is_invalid_signature):
        special_print('- [red] Tor could not be found')
        tor_status = 'error'

    if not tor_status == 'error':
        for i in range(10):
            if is_key_imported(TOR_FINGERPRINT[2:]):
                break

            is_error = False

            with status.status('[green]Loading Tor Keys from ' + pgp_key_server):
                command = [gnupg_path, '--keyserver', pgp_key_server,
                            '--recv-keys', TOR_FINGERPRINT]
                is_error, _, stderr, return_code = run_command(command)

            if is_error:
                special_print(f'- [red]Key Import Exception: {stderr}')
            else:
                parsed_pgp_output = parse_pgp_import_output(stderr)

                if (parsed_pgp_output['is_error'] and parsed_pgp_output['error'] is None):
                    special_print(f'- [red]Key Import Exception: Code {return_code}; '+
                                  'Exception: `Unknown error`')
                    is_error = True
                elif return_code != 0 or parsed_pgp_output['is_error']:
                    special_print(f'- [red]Key Import Exception: Code {return_code}; '+
                                  f'Exception: `{parsed_pgp_output['error']}`')
                    is_error = True
                else:
                    special_print(f'- [cyan]Key imported: `{parsed_pgp_output['owner']}`'+
                                  f'; processed: {str(parsed_pgp_output['processed'])}'+
                                  f', changed: {str(parsed_pgp_output['changed'])}')
                    break

            if is_error:
                if i >= 3:
                    continue_without_signature = input('Would you like to continue'+
                                                       ' without a valid signature?'+
                                                       ' [y / n] ')
                    if continue_without_signature.lower().startswith('y'):
                        is_invalid_signature = True
                        break

        if not is_invalid_signature:
            is_error = False

            with status.status('[green]Verifying the signature'):
                command = [gnupg_path, '--verify', tor_bundle_signature_file_path,
                           tor_bundle_file_path]
                is_error, _, stderr, return_code = run_command(command)

            if is_error:
                special_print(f'- [red]Signature validation error: {stderr}')
            else:
                parsed_pgp_output = parse_pgp_verify_output(stderr)

                if (parsed_pgp_output['is_error'] and parsed_pgp_output['error'] is None):
                    special_print('- [red]Signature validation error: Code '+
                                        f'{return_code}; Exception: `Unknown error`')
                    is_error = True
                elif return_code != 0 or parsed_pgp_output['is_error']:
                    special_print('- [red]Signature validation error: Code '+
                                        f'{return_code}; Exception: '+
                                        f'`{parsed_pgp_output['error']}`')
                    is_error = True
                else:
                    special_print('- [cyan]Signature valid: '+
                                        parsed_pgp_output['message'])

            if is_error:
                continue_without_signature = input('Would you like to continue'+
                                                    ' without a valid signature?'+
                                                    ' [y / n] ')
                if not continue_without_signature.lower().startswith('y'):
                    tor_status = 'error'

        if not tor_status == 'error':
            if os.path.exists(TOR_DIR_PATH) and required_install:
                shutil.rmtree(TOR_DIR_PATH)

            with status.status('[green]Extracting the Tor Bundle'):
                extract_tar(tor_bundle_file_path, TOR_DIR_PATH)

        with status.status('[green]Cleaning up (that may take a while)'):
            SecureDelete.directory(TEMP_DIR_PATH)

        tor_status = 'installed'

    return tor_status


def bridge_installer(bridge_type: str, use_bridgedb: bool,
                     user_agents: Optional[UserAgents] = None,
                     proxies: Optional[Proxies] = None,
                     status: Optional[StatusWrapper] = None,
                     data: Optional[Data] = None) -> list:
    """
    Downloads and installs bridges for a specific bridge type,
    either from BridgeDB or built-in sources.

    :param bridge_type: The type of bridges to install.
    :param use_bridgedb: Flag indicating whether to use BridgeDB for downloading bridges.
    :param user_agents: Optional. An object providing a pool of user agents for HTTP requests.
    :param proxies: Optional. An object providing a pool of proxies for routing requests.
    :param status: Optional. A wrapper for managing the status of the installation process.
    :return: A list of downloaded bridges.
    """

    if data is None:
        data = Data()

    clear_console()
    special_print('== [green]Bridge download[reset] ==')

    if data[bridge_type] is not None:
        return data[bridge_type]

    if use_bridgedb:
        url = 'https://bridges.torproject.org/bridges/?transport='\
              + {'vanilla': '0'}.get(bridge_type, bridge_type)

        fail_counter = 0
        bridge_site = None
        while True:
            if fail_counter > 5:
                special_print('- [red]Bridges could not be downloaded from'+
                              ' BridgeDB after 6 attempts, built-in bridges are used.')
                input('Enter: ')
                return TorBridges.get_default(bridge_type)

            if bridge_site is None:
                with status.status('[green]Requesting a captcha from BridgeDB'):
                    content, working_proxy = request(url, user_agents = user_agents,
                                                     proxies = proxies, status = status,
                                                     return_working_proxy = True)

                    if not isinstance(content, str):
                        fail_counter += 1
                        continue

                    output = bridgedb_extract_captcha(content)
                    if output is None:
                        fail_counter += 1
                        continue

                    bridge_site = content

            image_bytes, challenge_value = bridgedb_extract_captcha(bridge_site)
            bridge_site = None

            if None in [image_bytes, challenge_value]:
                fail_counter += 1
                sleep(1)
                continue

            ascii_img = image_bytes_to_ascii(image_bytes)

            while True:
                clear_console()
                special_print('== [green]Bridge download[reset] ==')
                print(ascii_img)

                captcha_input = input('Enter the letters and numbers you see: ')

                if captcha_input.strip() == "":
                    continue

                if len(captcha_input) < 5 or len(captcha_input) > 10:
                    special_print('\n- [red]The character string entered is '+
                                    'too long or too short')
                elif re.compile(r'[^a-zA-Z0-9]').search(captcha_input):
                    special_print('\n- [red]The entered character string contains '+
                                    'characters that cannot occur')
                else:
                    break

                input('Enter: ')

            form_data = {
                "captcha_response_field": captcha_input,
                "captcha_challenge_field": challenge_value
            }

            with status.status('[green]Checking the captcha and requesting bridges'):
                content, working_proxy = request(
                    url, 'POST', form_data, user_agents = user_agents, proxies = proxies,
                    status = status, specific_proxy = working_proxy, return_working_proxy = True
                )

                if not isinstance(content, str):
                    fail_counter += 1
                    continue

                bridges = bridgedb_extract_bridges(content)
                bridge_site = content

            if not isinstance(bridges, list) or not len(bridges) >= 1:
                fail_counter += 1
                special_print('- [red] Your input was not correct, try again!')
                input('Enter: ')
                continue

            break
    else:
        bridge_number_threshold = {"vanilla": 800, "obfs4": 5000}.get(bridge_type, 20)

        bridges = []
        for i in range(2):
            url_prefix = BRIDGE_URLS['main']
            if i >= 1:
                url_prefix = BRIDGE_URLS['backup']

            unformatted_bridges = request(
                url_prefix + bridge_type, operation_name = bridge_type.upper() + ' Bridges',
                user_agents = user_agents, proxies = proxies, status = status
            )

            if unformatted_bridges is not None:
                bridges = [line.strip() for line in unformatted_bridges.split('\n')\
                            if line.strip() != ""]
                bridges = list(dict.fromkeys(bridges).keys())

                if not len(bridges) > bridge_number_threshold:
                    bridges = []
                    continue
                break

        if len(bridges) == 0:
            special_print('- [red]Bridges could not be queried, '+
                            'site may be down or compromised.')
            input('Enter: ')
            return TorBridges.get_default(bridge_type)

    data[bridge_type] = bridges

    return bridges
