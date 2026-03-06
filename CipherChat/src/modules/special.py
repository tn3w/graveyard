import os
import sys
import secrets
from http.client import IncompleteRead
import subprocess
import atexit
import socket
import random
from time import time, sleep
from typing import Union, Optional, Tuple
from urllib.parse import urlparse, urlencode
import hashlib
import json
from threading import Thread
import concurrent.futures
from contextlib import contextmanager
import urllib.request
import urllib.error


try:
    from src.modules import socks
    from src.modules.cons import DATA_DIR_PATH, DEFAULT_USER_AGENT,\
        DUMMY_CRAWLER_USER_AGENT_HEADER, DEFAULT_BRIDGES_FILE_PATH, PROXY_SSL_CONTEXT,\
        TOR_DEFAULT_BRIDGES_FILE_PATH, PACKAGE_MANAGERS, CURRENT_DIR_PATH
    from src.modules.utils import JSON, StatusWrapper, Progress, special_print, dummy_cm,\
         check_permissions, run_command, cache, use_context_manager
except ImportError:
    import socks
    from cons import DATA_DIR_PATH, DEFAULT_USER_AGENT, DUMMY_CRAWLER_USER_AGENT_HEADER,\
         DEFAULT_BRIDGES_FILE_PATH,PROXY_SSL_CONTEXT, TOR_DEFAULT_BRIDGES_FILE_PATH,\
         PACKAGE_MANAGERS, CURRENT_DIR_PATH
    from utils import JSON, StatusWrapper, Progress, special_print, dummy_cm,\
         check_permissions, run_command, cache, use_context_manager


@contextmanager
def use_proxy(proxy: str):
    """
    A context manager for temporarily using a SOCKS5 proxy.

    :param proxy: A string representing the SOCKS5 proxy in the format 'ip:port'.
    """

    original_socket = socket.socket
    try:
        ip, port = proxy.split(":")
        socket.setdefaulttimeout(3)
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, ip, int(port))
        socket.socket = socks.socksocket
        yield
    finally:
        socks.setdefaultproxy(None)
        socket.socket = original_socket


class Data(dict):

    def __init__(self, file_path: Optional[str] = None,\
                 password: Optional[str] = None):
        self.password = password

        if not os.path.exists(DATA_DIR_PATH):
            os.makedirs(DATA_DIR_PATH, exist_ok = True)

        file_path = os.path.join(DATA_DIR_PATH, 'data.json') if not file_path else None
        self.file_path = file_path

        self.file_content = JSON.load(file_path, {})

        atexit.register(self._at_exit)
        super().__init__()

    def _at_exit(self) -> None:
        JSON.dump(self.file_content, self.file_path)

    def __setitem__(self, key: str, value: any) -> None:
        self.file_content[key] = value

        save_thread = Thread(target = self._at_exit)
        save_thread.start()

    def __getitem__(self, key: str) -> Optional[any]:
        try:
            return self.file_content[key]
        except KeyError:
            return None


class UserAgents:
    """
    Includes all functions that have something to do with user agents
    """

    def __init__(self, data: Optional[Data] = None):
        if data is None:
            data = Data()

        user_agents = []

        user_agent_data = data['user_agents']
        if isinstance(user_agent_data, dict):
            if isinstance(user_agent_data.get('time'), int) and\
                isinstance(user_agent_data.get('user_agents'), list):

                if len(user_agent_data['user_agents']) > 5:
                    if int(time()) - int(user_agent_data['time']) <= 604800:
                        user_agents = user_agent_data['user_agents']

        if len(user_agents) == 0:
            newest_user_agents = self._request_newest_user_agents()
            if isinstance(newest_user_agents, list) and len(newest_user_agents) > 5:
                user_agents = newest_user_agents
                data['user_agents'] = {'time': int(time()), 'user_agents': newest_user_agents}
            else:
                user_agents = [DEFAULT_USER_AGENT]

        self.user_agents = user_agents

    def get_ua(self) -> str:
        """
        Function to get a User Agent
        """

        return random.choice(self.user_agents)

    @staticmethod
    def _request_newest_user_agents():
        """
        This method requests the newest user agents from an API and
        returns a list of up to 10 user agents.

        :return: A list of up to 10 newest user agents,
                 or None if the request fails or no user agents are available.
        """

        try:
            url = 'https://www.useragents.me'

            socket.setdefaulttimeout(3)
            req = urllib.request.Request(url, headers=DUMMY_CRAWLER_USER_AGENT_HEADER)

            with urllib.request.urlopen(req, timeout = 3) as response:
                content: bytes = response.read()
                content = content.decode('utf-8').strip()

                raw_user_agents = content\
                    .split('<textarea class="form-control" rows="8">')[1]\
                    .split('</textarea>')[0]

                data = json.loads(raw_user_agents)

                if len(data) < 10:
                    return None

                new_user_agents = [user_agent_data['ua'] for user_agent_data in data]
                return new_user_agents[:10]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass

        return None


class Proxies:
    "Includes all functions that have something to do with proxies"

    def __init__(self, data: Optional[Data] = None):
        if data is None:
            data = Data()

        proxies = []

        proxy_data = data['proxies']
        if isinstance(proxy_data, dict):
            if isinstance(proxy_data.get('time'), int) and\
                isinstance(proxy_data.get('proxies'), list):

                if len(proxy_data['proxies']) > 5:
                    if int(time()) - int(proxy_data['time']) <= 7200:
                        proxies = proxy_data['proxies']

        if len(proxies) == 0:
            newest_proxies = self._request_newest_proxies()
            if isinstance(newest_proxies, list) and len(newest_proxies) > 5:
                proxies = newest_proxies
                data['proxies'] = {"time": int(time()), "proxies": newest_proxies}
            else:
                special_print('(Critical Error) Proxies could not be loaded, '+\
                              'the proxy server may be down or may have been compromised')
                sys.exit(2)

        self.proxies = proxies

        self.selected_time = None
        self.selected_proxies = None
        self.used_proxies = None

        self.update_proxies_running = False

    def update_proxies(self, status: StatusWrapper = None, check: bool = False) -> list:
        """
        Updates the proxy list for subsequent usage.

        :return: If the update process succeeds, returns a list of selected proxies
        """

        if self.update_proxies_running:
            return

        if check:
            if isinstance(self.selected_time, int) and isinstance(self.selected_proxies, list):
                if int(time()) - int(self.selected_time) <= 1800:
                    if self.used_proxies is None:
                        self.used_proxies = []

                    unused_proxies = [
                        proxy for proxy in self.selected_proxies if proxy not in self.used_proxies
                        ]
                    if not len(unused_proxies) == 0:
                        return

        self.update_proxies_running = True
        self.selected_time, self.selected_proxies, self.used_proxies\
            = None, None, None

        try:
            if not status is None:
                with status.status('[green]The latest proxies are being updated'+
                            ' (this could take a few minutes)'):
                    choosen_proxies = self._select_random(self.proxies[:100], 50)
            else:
                choosen_proxies = self._select_random(self.proxies[:100], 50)

            self.selected_time = int(time())
            self.selected_proxies = choosen_proxies

            self.used_proxies = []
        finally:
            self.update_proxies_running = False

        return choosen_proxies

    def get_proxy(self, status: StatusWrapper = None, quite: bool = False) -> str:
        """
        Function to get a proxy
        """

        def random_proxy(proxies: list) -> str:
            if len(proxies) <= 0:
                return None

            if len(proxies) == 1:
                random_proxy = proxies[0]
            else:
                random_proxy = random.choice(proxies)
            self.used_proxies.append(random_proxy)

            return random_proxy

        if isinstance(self.selected_time, int) and isinstance(self.selected_proxies, list):
            if int(time()) - int(self.selected_time) <= 1800:
                if self.used_proxies is None:
                    self.used_proxies = []

                unused_proxies = [
                    proxy for proxy in self.selected_proxies if proxy not in self.used_proxies
                    ]
                if not len(unused_proxies) == 0:
                    if len(unused_proxies) == 1:
                        if quite:
                            status = None

                        t = Thread(target = self.update_proxies, args = (status,))
                        t.start()

                        return unused_proxies[0]

                    return random_proxy(unused_proxies)

        update_proxies = True
        if self.update_proxies_running:
            for _ in range(300):
                if self.selected_proxies is not None:
                    update_proxies = False
                    break
                sleep(0.1)

        if update_proxies:
            self.update_proxies_running = False

            choosen_proxies = self.update_proxies(status)
            return random_proxy(choosen_proxies)

        unused_proxies = [
            proxy for proxy in self.selected_proxies
            if proxy not in self.used_proxies
        ]
        return random_proxy(unused_proxies)

    @staticmethod
    def _request_newest_proxies() -> Optional[list]:
        """
        Requests the newest proxies from a specified source and filters
        them based on certain criteria.

        :return: A list of dictionaries representing the filtered proxies.
        """

        try:
            url = 'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies'+\
                  '&protocol=socks5&country=FR,DE,NL,CH,GB,US,CA,AU,NO,SE,DK,FI,AT,IE,IS,NZ'+\
                  ',LU,JP,SG,HK&anonymity=elite&timeout=3000&proxy_format=ipport&format=json'

            socket.setdefaulttimeout(3)
            req = urllib.request.Request(url, headers=DUMMY_CRAWLER_USER_AGENT_HEADER)

            with urllib.request.urlopen(req, timeout = 3) as response:
                request_data = json.load(response)

                proxies = request_data['proxies']
                sorted_proxies = sorted(proxies,
                                        key=lambda x: (x["average_timeout"], -x["uptime"]),
                                        reverse=False)
                filtered_proxies = [proxy for proxy in sorted_proxies if proxy["alive"]]
                return [proxy['ip'] + ':' + str(proxy['port']) for proxy in filtered_proxies]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass

        return None

    @staticmethod
    def _is_proxy_online(proxy: str):
        """
        Checks if a proxy is online by attempting a connection.

        :param proxy: Proxy in the format "ip:port"
        :return: True if the proxy is online, False otherwise
        """

        try:
            ip, _ = proxy.split(":")
            with use_proxy(proxy):
                with urllib.request.urlopen(
                    'https://checkip.amazonaws.com/', context = PROXY_SSL_CONTEXT, timeout = 3
                    ) as response:

                    content: bytes = response.read()
                    content = content.decode('utf-8').strip()

                    if not str(ip) == content:
                        return False

        except (socket.timeout, socket.error, urllib.error.URLError):
            return False
        return True

    @staticmethod
    def _select_random(proxys: list, quantity: int = 1) -> Union[list, str]:
        """
        Selects random proxys that are online using concurrent.futures.

        :param proxys: A list of all existing proxies
        :param quantity: How many proxys should be selected
        """

        selected_proxies = []

        with concurrent.futures.ThreadPoolExecutor(max_workers = 25) as executor:
            futures = {executor.submit(Proxies._is_proxy_online, proxy): proxy for proxy in proxys}

            for future in concurrent.futures.as_completed(futures):
                if len(selected_proxies) >= quantity:
                    break

                proxy = futures[future]
                try:
                    if future.result():
                        selected_proxies.append(proxy)
                except (AttributeError, TypeError):
                    pass

            for remaining_future in futures:
                remaining_future.cancel()

        selected_proxies = selected_proxies[:quantity]

        if quantity == 1:
            return selected_proxies[0]

        return selected_proxies


class TorBridges:
    """
    A collection of functions for managing Tor bridges.
    """

    def __init__(self, bridges: list, use_bridgedb: bool = False):
        """
        Initializes the TorBridges object with a list of bridges and a flag indicating
        whether to use BridgeDB for bridge acquisition.

        :param bridges: A list of Tor bridges.
        :param use_bridgedb: Flag indicating whether to use BridgeDB. Defaults to False.
        """

        self.bridges = bridges
        self.use_bridgedb = use_bridgedb

    @staticmethod
    def _get_type(bridge_str: str) -> str:
        """
        Returns the type of a given bridge
        
        :param bridge_str: A string representing the bridge address.
        """

        for bridge_type in ['obfs4', 'webtunnel', 'snowflake', 'meek_lite']:
            if bridge_str.startswith(bridge_type):
                return bridge_type
        return "vanilla"

    @staticmethod
    def _is_vanilla_bridge_online(bridge_str: str) -> bool:
        """
        Checks if a vanilla bridge is online.

        :param bridge_str: A string representing the bridge address.
        :return: True if the vanilla bridge is online, False otherwise.
        """

        try:
            bridge_ip, bridge_port = bridge_str.split()[0].split(':')
            with socket.create_connection((bridge_ip, int(bridge_port)), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError):
            pass

        return False

    @staticmethod
    def _is_obfs4_bridge_online(bridge_str: str) -> bool:
        """
        Checks if an obfs4 bridge is online.

        :param bridge_str: A string representing the obfs4 bridge address.
        :retunr: True if the obfs4 bridge is online, False otherwise.
        """

        try:
            bridge_ip, bridge_port = bridge_str.split()[1].split(':')[1:3]
            with socket.create_connection((bridge_ip, int(bridge_port)), timeout=2) as obfs4_sock:
                obfs4_sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                response = obfs4_sock.recv(4096)

                if response:
                    return True
        except (socket.timeout, ConnectionRefusedError):
            pass

        return False

    @staticmethod
    def _is_webtunnel_bridge_online(bridge_str: str) -> bool:
        """
        Checks if a webtunnel bridge is online.

        :param bridge_str: A string representing the webtunnel bridge address.
        :return: True if the webtunnel bridge is online, False otherwise.
        """

        try:
            bridge_ip = bridge_str.split()[1][1:-1].split(':')[0]
            bridge_port = int(bridge_str.split()[1][1:-1].split(':')[1])
            with socket.create_connection((bridge_ip, bridge_port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError):
            pass

        return False

    @staticmethod
    @cache(seconds = 60)
    def is_bridge_online(bridge_str: str, bridge_type: Optional[str] = None) -> bool:
        """
        Determines if a bridge is online based on its type.

        :param bridge_str: A string representing the bridge address.
        :param bridge_type: The type of the bridge. If not provided, it will be automatically
                            determined based on the bridge string. Defaults to None.
        :return: True if the bridge is online, False otherwise.
        """

        if not isinstance(bridge_type, str):
            bridge_type = TorBridges._get_type(bridge_str)

        if bridge_type not in ['vanilla', 'obfs4', 'webtunnel']:
            return True

        bridge_type_mapping = {
            'vanilla': TorBridges._is_vanilla_bridge_online,
            'obfs4': TorBridges._is_obfs4_bridge_online,
            'webtunnel': TorBridges._is_webtunnel_bridge_online
        }

        return bridge_type_mapping.get(bridge_type)(bridge_str)

    @staticmethod
    @cache(seconds = 3600)
    def get_default(bridge: Optional[str] = None) -> Optional[Union[dict, list]]:
        """
        Retrieve the default bridges configuration from the JSON file and
        optionally filter by bridge type.

        :param bridge: Optional. The type of bridge to retrieve.
                       If specified, only bridges of this type will be returned.
        :return: If `bridge` is specified, returns a list of default bridges of the specified type. 
                 Otherwise, returns a dictionary containing all default bridges configurations.
        """

        bridges = JSON.load(DEFAULT_BRIDGES_FILE_PATH)

        if os.path.exists(TOR_DEFAULT_BRIDGES_FILE_PATH):
            tor_bridges = JSON.load(TOR_DEFAULT_BRIDGES_FILE_PATH)

            for bridge_type, default_bridges in tor_bridges['bridges']:
                if bridge_type == 'meek-azure':
                    bridge_type = 'meek_lite'

                bridges[bridge_type] = default_bridges

        if isinstance(bridge, str):
            return bridges.get(bridge)

        return bridges

    def get_random(self, quantity: int = 2) -> list:
        """
        Retrieves a random selection of bridges.

        :param quantity: The number of bridges to retrieve. Defaults to 2.
        :return: A list of randomly selected bridges.
        """

        if len(self.bridges) <= quantity:
            return self.bridges[:quantity]

        selected_bridges = []
        if self.use_bridgedb:
            while True:
                random_bridge = secrets.choice(self.bridges)
                if random_bridge in selected_bridges:
                    continue

                selected_bridges.append(random_bridge)
                if len(selected_bridges) >= quantity:
                    break
            return selected_bridges

        with concurrent.futures.ThreadPoolExecutor(max_workers = 25) as executor:
            futures = {executor.submit(self.is_bridge_online, bridge):
                       bridge for bridge in self.bridges}

            for future in concurrent.futures.as_completed(futures):
                if len(selected_bridges) >= quantity:
                    break

                bridge = futures[future]
                try:
                    if future.result():
                        selected_bridges.append(bridge)
                except (AttributeError, TypeError):
                    pass

            for remaining_future in futures:
                remaining_future.cancel()

        selected_bridges = selected_bridges[:quantity]

        return selected_bridges


class Linux:
    """
    Collection of functions that have something to do with Linux
    """

    @staticmethod
    @cache(seconds = 3600)
    def get_package_manager() -> Tuple[Optional[str], Optional[str]]:
        """
        Returns the Packet Manager install command and the update command
        """

        for package_manager in PACKAGE_MANAGERS:
            try:
                subprocess.check_call(package_manager["version_command"], shell=True)
            except (subprocess.CalledProcessError, PermissionError,
                    subprocess.SubprocessError, subprocess.CalledProcessError,
                    OSError, subprocess.TimeoutExpired):
                pass
            else:
                return package_manager["installation_command"], package_manager["update_command"]

        return None, None

    @staticmethod
    def install_package(package_name: str, package_manager: Tuple[str, str]) -> bool:
        """
        Attempts to install a Linux package
        
        :param package_name: Name of the Linux packet
        :param package_manager: Package Manager installations and update command in one tuple
        """

        installation_command, update_command = package_manager

        command = ['sudo'] + update_command.split()
        is_error, _, _, return_code = run_command(command, True)

        if is_error or return_code != 0:
            return False

        command = ['sudo'] + installation_command.split() + [package_name, '-y']
        is_error, _, _, return_code= run_command(command, True)

        if is_error or return_code != 0:
            return False

        return True


def macos_get_installer_and_volume_path() -> Tuple[Optional[str], Optional[str]]:
    """
    Function to automatically detect the macOS installer and the volume path
    """

    installer_path = None

    mounted_volumes = [volume for volume in os.listdir("/Volumes") if not volume.startswith(".")]
    if mounted_volumes:
        volume_name = mounted_volumes[0]
        volume_path = os.path.join("/Volumes", volume_name)

        for root, _, files in os.walk(volume_path):
            for file in files:
                if file.endswith(".app"):
                    installer_path = os.path.join(root, file)
                    break
    else:
        return None, None

    return installer_path, volume_path


def download_file(url: str, dict_path: Optional[str] = None,
                  operation_name: Optional[str] = None,
                  file_name: Optional[str] = None,
                  default_length: int = 500000,
                  user_agents: Optional[UserAgents] = None,
                  proxies: Optional[Proxies] = None,
                  status: Optional[StatusWrapper] = None) -> Union[str, int]:
    """
    Downloads a file from the specified URL and saves it to the given directory path.

    :param url: The URL of the file to download.
    :param dict_path: The directory path where the file will be saved. 
    :param operation_name: A name to describe the download operation. 
    :param file_name: The name to save the downloaded file as. 
    :param default_length: The default length of the file if the content length
                           cannot be determined.
    :param user_agents: An instance of UserAgents for selecting a random user-agent string.
    :param proxies: An instance of Proxies for handling proxy configurations. 
    :param status: An instance of StatusWrapper for managing status updates. 
    :return: The path to the downloaded file if successful, otherwise None.
    """

    operation_name = url if operation_name is None else operation_name

    if file_name is None:
        parsed_url = urlparse(url)
        file_name = os.path.basename(parsed_url.path)

    if dict_path is None or not os.path.exists(dict_path):
        dict_path = CURRENT_DIR_PATH

    save_path = os.path.join(dict_path, file_name)

    if os.path.isfile(save_path) or not check_permissions(save_path, 'w'):
        return save_path

    if proxies is not None:
        proxies.update_proxies(status, check = True)

    while True:
        if user_agents is not None:
            random_ua = user_agents.get_ua()
        else:
            random_ua = DEFAULT_USER_AGENT

        context_manager = dummy_cm

        context = None

        kwargs = {}
        if proxies is not None:
            proxy = proxies.get_proxy(status, quite = True)
            kwargs["proxy"] = proxy
            context_manager = use_proxy
            context = PROXY_SSL_CONTEXT

        progress = Progress('[green]Downloading '+
                            operation_name + '[reset]', total = default_length,
                            is_download = True)

        with context_manager(**kwargs):
            try:
                with open(save_path, 'ab') as file:
                    req = urllib.request.Request(url, headers={'User-Agent': random_ua})
                    with urllib.request.urlopen(req, timeout = 3,
                            context = context) as response:
                        if response.getcode() != 200:
                            return response.getcode()

                        downloaded_bytes = 0
                        total_length = response.length
                        progress.total = default_length if total_length is None\
                                         else int(total_length)

                        while True:
                            chunk = response.read(1024)
                            if not chunk:
                                if not downloaded_bytes >= total_length:
                                    raise IncompleteRead(downloaded_bytes, total_length)
                                break

                            file.write(chunk)
                            downloaded_bytes += len(chunk)
                            progress.update(downloaded_bytes)
            except (urllib.error.URLError, urllib.error.HTTPError,
                    socket.timeout, IncompleteRead):
                sleep(1)
                os.remove(save_path)
                continue

        return save_path


def request(url: str, method: str = 'GET',
            form_data: Optional[dict] = None,
            operation_name: Optional[str] = None,
            user_agents: Optional[UserAgents] = None,
            proxies: Optional[Proxies] = None,
            status: Optional[StatusWrapper] = None,
            specific_proxy: Optional[str] = None,
            return_working_proxy: bool = False)\
            -> Union[Optional[str], Tuple[Optional[str], str]]:
    """
    Send an HTTP request to the specified URL using the specified method and parameters.

    :param url: The URL to which the request will be sent.
    :param method: The HTTP method to be used for the request (default is 'GET').
    :param form_data: A dictionary containing form data to be included in the request payload.
    :param operation_name: A name to describe the download operation. 
    :param user_agents: An object providing a pool of user agents to rotate for the request headers.
    :param proxies: An object providing proxy rotation for the request.
    :param status: A wrapper for managing the status of the request process.
    :return: The response content as a string if the request is successful, otherwise None.
    """

    if not isinstance(method, str):
        method = 'GET'

    is_post_method = 'post' == method.lower()

    if operation_name is None:
        operation_name = url

    content = None
    proxy = None

    if proxies is not None:
        proxies.update_proxies(status, check = True)

    status_context_manager, status_kwargs = use_context_manager(
        status, message = '[cyan]Requesting ' + operation_name
    )

    with status_context_manager(**status_kwargs):
        for _ in range(20):
            if user_agents is not None:
                random_ua = user_agents.get_ua()
            else:
                random_ua = DEFAULT_USER_AGENT

            context_manager = dummy_cm
            context = None

            kwargs = {}
            if proxies is not None or specific_proxy is not None:
                if specific_proxy is not None:
                    proxy = specific_proxy
                else:
                    proxy = proxies.get_proxy(status, quite = True)
                kwargs["proxy"] = proxy
                context_manager = use_proxy
                context = PROXY_SSL_CONTEXT

            with context_manager(**kwargs):
                try:
                    headers = {'User-Agent': random_ua}

                    if is_post_method:
                        headers['Content-Type'] = 'application/x-www-form-urlencoded'

                    data = None
                    if is_post_method and isinstance(form_data, dict):
                        data = urlencode(form_data).encode('ascii')

                    method = 'POST' if is_post_method else 'GET'

                    req = urllib.request.Request(
                        url, data = data, headers = headers, method = method
                    )
                    with urllib.request.urlopen(req, data = data, timeout = 3,
                                                context = context) as response:
                        content: bytes = response.read()
                        content = content.decode('utf-8').strip()
                except (urllib.error.URLError, urllib.error.HTTPError,
                        socket.timeout, IncompleteRead):
                    sleep(1)
                else:
                    break

    if return_working_proxy:
        return content, proxy

    return content


@cache(seconds = 3600)
def is_password_pwned(password: str, user_agents: Optional[UserAgents] = None,
                      status: Optional[StatusWrapper] = None) -> bool:
    """
    Ask pwnedpasswords.com if password is available in data leak

    :param password: Password to check against
    :param user_agents: An object providing random User-Agent strings.
    :param status: An object wrapping status information.
    """

    password_sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    hash_prefix = password_sha1_hash[:5]

    url = f"https://api.pwnedpasswords.com/range/{hash_prefix}"

    response = request(url, user_agents, None, status)

    hashes = [line.strip().split(':')[0] for line in response.split('\n')]
    for hash_str in hashes:
        if hash_str == password_sha1_hash[5:]:
            return True
    return False


def is_key_imported(fingerprint: str) -> bool:
    """
    Check if a GPG key with a specified fingerprint is imported.

    :param fingerprint: The fingerprint of the GPG key to check for (str).
    :return: True if the key with the specified fingerprint is imported, otherwise False.
    """

    command = ["gpg", "--list-keys", "--with-fingerprint", "--with-colons"]

    is_error, stdout, _, return_code = run_command(command)

    if is_error or return_code != 0:
        return False

    output_lines = stdout.splitlines()
    for line in output_lines:
        if line.startswith("fpr:") and fingerprint.lower() in line.lower():
            return True

    return False


def parse_pgp_import_output(output: Optional[str]) -> dict:
    """
    Parses the output of a PGP key import operation and returns relevant information.

    :param output: The output of the PGP key import operation.
    :return: A dictionary containing parsed information including whether an error occurred,
             the error message (if any), the owner of the key (if applicable), the number of keys
             that were changed, and the total number of keys processed.
    """

    data = {
        'is_error': False,
        'error': None,
        'owner': None,
        'processed': 0,
        'changed': 0
    }

    if output is None:
        data['is_error'] = True
        return data

    if not output.startswith('gpg: key '):
        data['is_error'] = True
        data['error'] = output.replace('gpg: ', '').strip()
        return data

    start_index = output.find('"') + 1
    end_index = output.find('"', start_index)
    key_owner = output[start_index:end_index]
    data['owner'] = key_owner

    processed_index = output.find("Total number processed:") + len("Total number processed:")
    processed_end_index = output.find("\r\n", processed_index)
    total_processed = int(output[processed_index:processed_end_index].strip())

    data['processed'] = total_processed

    if 'unchanged:' in output:
        unchanged_index = output.find("unchanged:") + 10
        unchanged_end_index = output.find("\r\n", unchanged_index)
        unchanged_count = int(output[unchanged_index:unchanged_end_index].strip())
    else:
        unchanged_count = 0

    changed_count = total_processed - unchanged_count
    data['changed'] = changed_count
    return data


def parse_pgp_verify_output(output: Optional[str]) -> dict[str]:
    """
    Parse the output of a PGP verification process and extract relevant information.

    :param output: The output of the PGP verification process.
    :return: A dictionary containing the parsed information.
    """

    data = {
        'is_error': False,
        'error': None,
        'message': None
    }

    if output is None:
        data['is_error'] = True
        return data

    error = ''
    for i, line in enumerate(output.split('\n')):
        line = line.strip()
        if line.startswith('gpg: Good signature'):
            line = line.replace('gpg: ', '').replace('"', '`')
            data['message'] = '`'.join(line.split('`')[:2]) + '`'

            return data

        line = line.replace('gpg: ', '')
        if not line in error:
            if line.endswith('.'):
                line = line [:-1]
            error += line
            if i < 2:
                error += ' - '
            else:
                break

    data['is_error'] = True
    data['error'] = error
    return data
