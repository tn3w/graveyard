import sys
import os
from time import time
from sys import argv as ARGUMENTS
from src.modules.cons import HELP_COMMANDS, VERSION, CURRENT_DIR_PATH, DATA_DIR_PATH,\
     OS, TOR_EXECUTABLE_PATH, PGP_KEY_SERVERS
from src.modules.utils import StatusWrapper, SecureDelete, clear_console,\
     get_parameters_after_argument, get_recycle_bin_path, special_print,\
     selection
from src.modules.special import Proxies, UserAgents, TorBridges, Data
from src.modules.pip_installer import install_package

if __name__ != '__main__':
    sys.exit(2)


###########################
######## Arguments ########
###########################


if '-h' in ARGUMENTS or '--help' in ARGUMENTS:
    ARGUMENT = '-h' if '-h' in ARGUMENTS else '--help'
    following_parameters = get_parameters_after_argument(ARGUMENT, ARGUMENTS, ignore_dashes = False)

    NOT_FOUND_ERROR = None

    if len(following_parameters) != 0:
        following_parameters = [param.replace('-', '') for param in following_parameters]
        REQUESTED_COMMAND = None
        for command in HELP_COMMANDS:
            for command_argument in command['arguments']:
                if command_argument.replace('-', '') in following_parameters:
                    REQUESTED_COMMAND = command

        if not REQUESTED_COMMAND is None:
            clear_console()
            special_print('== [green]' + REQUESTED_COMMAND['name'] + '[reset] ==')

            ARGUMENTS_TEXT = ''
            for i, argument in enumerate(REQUESTED_COMMAND['arguments']):
                ARGUMENTS_TEXT += argument
                if not len(REQUESTED_COMMAND['arguments']) == i + 1:
                    ARGUMENTS_TEXT += ', '

            print('Arguments:', ARGUMENTS_TEXT)
            print(REQUESTED_COMMAND['description'])

            if len(REQUESTED_COMMAND.get('parameters', [])) != 0:
                print('\nParameters:')
                for parameter in REQUESTED_COMMAND['parameters']:
                    special_print(
                        '- [yellow]' + parameter['name'] + '[reset] '\
                            + parameter['description'])

            if len(REQUESTED_COMMAND.get('examples', [])) != 0:
                print('\nExamples:')
                for example in REQUESTED_COMMAND['examples']:
                    special_print(
                        '- `[cyan]' + example['command'] + '[reset]` '\
                            + example['description'])
            sys.exit(0)
        else:
            NOT_FOUND_ERROR = following_parameters[0]

    clear_console()
    if NOT_FOUND_ERROR:
        special_print('[red][Error] No help information found for'+
                           f' parameter `{NOT_FOUND_ERROR}`\n')
    print('To start the client, do not use any of the following arguments:')
    if len(HELP_COMMANDS) == 0:
        print('*~ No help information found ~*\n')
        sys.exit(0)

    argument_lengths = []
    param_lengths = []
    for command in HELP_COMMANDS:
        ARGS_TEXT = ''
        for i, argument in enumerate(command['arguments']):
            ARGS_TEXT += argument
            if not len(command['arguments']) == i + 1:
                ARGS_TEXT += ', '

        argument_lengths.append(len(ARGS_TEXT))

        PARAMS_TEXT = ''
        used_parameters = []
        for pair in command.get('pairs', []):
            PARAMS_TEXT += '/'.join(pair) + ' '
            used_parameters.extend(pair)

        for parameter in command.get('parameters', []):
            param = parameter['name']
            if param not in used_parameters:
                PARAMS_TEXT += param + ' '

        param_lengths.append(len(PARAMS_TEXT))

    max_argument_length = max(*argument_lengths) + 1
    max_parameter_length = max(*param_lengths)

    for command in HELP_COMMANDS:
        COMMAND_TEXT = ''
        ARGUMENTS_TEXT = ''
        for i, argument in enumerate(command['arguments']):
            ARGUMENTS_TEXT += argument
            if not len(command['arguments']) == i + 1:
                ARGUMENTS_TEXT += ', '

        COMMAND_TEXT += '[cyan]' + ARGUMENTS_TEXT + '[reset]'
        COMMAND_TEXT += ' ' * (max_argument_length - len(ARGUMENTS_TEXT))

        PARAMETER_TEXT = ''

        used_parameters = []
        for pair in command.get('pairs', []):
            COMMAND_TEXT += '[yellow]' + '/'.join(pair) + '[reset] '
            PARAMETER_TEXT += '/'.join(pair) + ' '
            used_parameters.extend(pair)

        for parameter in command.get('parameters', []):
            param: str = parameter['name']
            if param not in used_parameters:
                COMMAND_TEXT += '[yellow]' + param + '[reset] '
                PARAMETER_TEXT += param + ' '

        COMMAND_TEXT += ' ' * (max_parameter_length - len(PARAMETER_TEXT))

        COMMAND_TEXT += command.get('short_description', '')
        special_print(COMMAND_TEXT)
    sys.exit(0)


if '-v' in ARGUMENTS or '--version' in ARGUMENTS:
    if VERSION is None:
        special_print('CipherChat Version: [red]n.a.[reset]\n')
        sys.exit(0)
    print('CipherChat Version:', VERSION, '\n')
    sys.exit(0)


if '-a' in ARGUMENTS or '--about' in ARGUMENTS:
    clear_console()
    if VERSION == 'n.a.':
        special_print('Current version: [red]' + VERSION + '[reset]\n')
    else:
        print('Current version:', VERSION, '\n')
    print('CipherChat is used for secure chatting with end to end encryption and anonymous',
          'use of the Tor network for sending / receiving messages, it is released under the',
          'GPL v3 on Github. Setting up and using secure chat servers is made easy.')
    special_print('Use `[cyan]python main.py -h[reset]` if you want to know all commands. ' +\
                       'To start use `[cyan]python main.py[reset]`.')
    sys.exit(0)


STATUS = StatusWrapper()


if '-k' in ARGUMENTS or '--killswitch' in ARGUMENTS:
    ARGUMENT = '-k' if '-k' in ARGUMENTS else '--killswitch'
    following_parameters = get_parameters_after_argument(ARGUMENT, ARGUMENTS)

    start_time = time()

    if 'all' in following_parameters:
        DELETE_ALL_FILES = True
    elif 'notall' in following_parameters:
        DELETE_ALL_FILES = False
    else:
        delete_all = input('Do you also want all files from CipherChat to be deleted? ')
        DELETE_ALL_FILES = delete_all.lower().startswith('y')

    if DELETE_ALL_FILES:
        delete_directory = CURRENT_DIR_PATH
    else:
        delete_directory = DATA_DIR_PATH

    if 'trash' in following_parameters:
        DELETE_TRASH = True
    elif 'nottrash' in following_parameters:
        DELETE_TRASH = False
    else:
        inp_delete_trash = input('Should the recycle bin be deleted as well? ')
        DELETE_TRASH = inp_delete_trash.lower().startswith('y')

    with STATUS.status('[green]All files are being securely deleted (Can take several minutes)'):
        if os.path.isdir(delete_directory):
            SHOW_COMMAND = SecureDelete.directory(delete_directory)
        else:
            SHOW_COMMAND = False

    if DELETE_TRASH:
        recyle_bin_path = get_recycle_bin_path(OS)
        if recyle_bin_path is not None:
            with STATUS.status('[green]Recycle bin is being emptied (Can take several minutes)'):
                SecureDelete.directory(recyle_bin_path)

    end_time = time()

    clear_console(False)
    if SHOW_COMMAND:
        if os.name == 'nt':
            command = f'cd .. & del /F /Q "{delete_directory}"'
        else:
            command = f'cd .. ; rm -rf {delete_directory}'
        print(f'To complete this process, use the following command: `{command}`')
    print(f'💩 Done. (took {str(round(end_time - start_time))} s)')

    sys.exit(0)


data = Data()
USER_AGENTS = UserAgents(data = data)

need_installation = []

try:
    from PIL import Image as _
except ImportError:
    need_installation.append('PIL')

if len(need_installation) != 0:
    print('~~ Automatic package installation ~~')

    for package in need_installation:
        install_package(package, USER_AGENTS, STATUS)

from src.modules.installation import tor_installer, get_configuration, bridge_installer


if '-i' in ARGUMENTS or '--installer' in ARGUMENTS:
    ARGUMENT = '-i' if '-i' in ARGUMENTS else '--installer'
    following_parameters = get_parameters_after_argument(ARGUMENT, ARGUMENTS)

    configuration = get_configuration(STATUS, False)

    clear_console()
    PROXIES = Proxies(data = data)
    if 'noproxy' in following_parameters:
        PROXIES = None
    elif configuration is None and not 'proxy' in following_parameters:
        use_proxies = input('Should proxies be used for installation? [y / n] ')
        if not use_proxies.lower().startswith('y'):
            PROXIES = None
    elif configuration is not None:
        if not configuration['installation']['proxies']:
            PROXIES = None

    VALIDATE_SIGNATURE = True
    if 'nocheck' in following_parameters:
        VALIDATE_SIGNATURE = False
    elif configuration is None and not 'check' in following_parameters:
        validate_signature_inp = input('Should signatures be verified? [y / n] ')
        if not validate_signature_inp.lower().startswith('y'):
            VALIDATE_SIGNATURE = False
    elif configuration is not None:
        if not configuration['installation']['signature_verification']:
            VALIDATE_SIGNATURE = False

    KEY_SERVER_PARAM = None
    for param in following_parameters:
        if not '-' in param and not\
            param in ['proxy', 'noproxy', 'check', 'nocheck']:
            KEY_SERVER_PARAM = param
            break

    KEY_SERVER = 'keys.openpgp.org'
    if KEY_SERVER_PARAM is not None:
        KEY_SERVER = KEY_SERVER_PARAM
    elif configuration is not None:
        KEY_SERVER = configuration['installation']['keyserver']
    else:
        KEY_SERVER = selection(
            PGP_KEY_SERVERS, 'key server', '', max_display = 5
        ).replace(' (Recommended)', '')

    tor_installer(True, VALIDATE_SIGNATURE, KEY_SERVER, USER_AGENTS, PROXIES, STATUS)

    sys.exit(0)


#############################
######## Client-Side ########
#############################


config = get_configuration(STATUS)

if config['installation']['proxies']:
    PROXIES = Proxies(data = data)
else:
    PROXIES = None

if not os.path.isfile(TOR_EXECUTABLE_PATH):
    installation_conf = config['installation']

    tor_installer(
        False,
        installation_conf['signature_verification'],
        installation_conf['keyserver'],
        USER_AGENTS, PROXIES, STATUS
    )

bridge_conf = config['bridges']

bridges = []
if bridge_conf['use']:
    if bridge_conf['buildin']:
        bridges = TorBridges.get_default(bridge_conf['type'])
    else:
        bridges = bridge_installer(
            bridge_conf['type'], bridge_conf['bridgedb'],
            USER_AGENTS, PROXIES, STATUS, data = data
        )
