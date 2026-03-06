import os
from threading import Thread
from time import time
from typing import Optional, Tuple, Any
from pkg_resources import resource_filename
from .utils import JSON, Hashing, SymmetricEncryption, generate_random_string, is_email


try:
    CURRENT_DIR_PATH = resource_filename('flask_AuthGenius', '')
except ModuleNotFoundError:
    CURRENT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))

DATA_DIR_PATH = os.path.join(CURRENT_DIR_PATH, 'data')


class UserSystem(dict):

    def __init__(self, users_file_path: Optional[str] = None) -> None:
        if users_file_path is None:
            users_file_path = os.path.join(DATA_DIR_PATH, 'users.json')
        self.users_file_path = users_file_path
        self.reserved_user_ids = []
        self.reserved_session_ids = []

        super().__init__()

    @property
    def _load(self) -> dict:
        return JSON.load(self.users_file_path, {})

    def _dump(self, new_users: dict) -> None:
        dump_thread = Thread(target = JSON.dump, args = (new_users, self.users_file_path))
        dump_thread.start()

    def update(self, user_id: Any, user_data: Any) -> None:
        users = self._load
        users[user_id] = user_data

        self._dump(users)

    def __getitem__(self, user_id: str) -> Tuple[Optional[str], Optional[dict]]:
        users = self._load

        for index in range(2):
            for hashed_user_id, user_data in users.items():
                if user_id == hashed_user_id:
                    return (hashed_user_id, user_data)

                if index == 1:
                    if Hashing().compare(user_id, hashed_user_id):
                        return (hashed_user_id, user_data)

        return (None, None)

    ############
    ### User ###
    ############

    def create_user(self, password: str, user_name: Optional[str] = None,
                    user_email: Optional[str] = None,
                    other_user_data: Optional[dict] = None,
                    encrypted_fields: Optional[list] = None) -> str:

        if other_user_data is None:
            other_user_data = {}
        if encrypted_fields is None:
            encrypted_fields = ['id']

        user = {}

        hashed_password = Hashing(iterations = 150000).hash(password)
        user['hpwd'] = hashed_password

        if not user_name is None:
            user['hname'] = Hashing().hash(user_name)
            other_user_data['name'] = user_name
        if not user_email is None:
            user['hemail'] = Hashing().hash(user_email)
            other_user_data['email'] = user_email

        user_id = generate_random_string(12, False)
        while None not in self[user_id] or user_id in self.reserved_user_ids:
            user_id = generate_random_string(12, False)

        self.reserved_user_ids.append(user_id)

        try:
            other_user_data['id'] = user_id

            encryptor = SymmetricEncryption(password).encrypt

            user_data = {}
            for key, value in other_user_data.items():
                if key in encrypted_fields:
                    value = encryptor(value)
                user_data[key] = value

            user['data'] = user_data

            users = self._load

            hashed_user_id = Hashing().hash(user_id)
            while any(user_id == hashed_user_id for user_id in list(users.keys())):
                hashed_user_id = Hashing().hash(user_id)

            self.update(hashed_user_id, user)
            return user_id
        finally:
            self.reserved_user_ids.remove(user_id)

    def get_user(self, user_id: Optional[str] = None,
                 user_name: Optional[str] = None,
                 user_email: Optional[str] = None,
                 password: Optional[str] = None,
                 encrypted_fields: Optional[list] = None,
                 decrypt_only_fields: Optional[list] = None,
                 return_id: bool = False) -> Optional[dict]:

        if not isinstance(encrypted_fields, dict):
            encrypted_fields = ['id']

        users = self._load

        user = None

        if user_id is not None:
            hashed_user_id, user_data = self[user_id]

            user = user_data.copy()
            if hashed_user_id is not None and return_id:
                user_data['id'] = user_id
                user_data['hid'] = hashed_user_id

        for index in range(2):
            if user is not None:
                break

            start = 'name'
            if not None in [user_name, user_email]:
                start = 'email' if is_email(user_email) else 'name'

            if index == 0 and start == 'name' or index == 1:
                if user is None and user_name is not None:
                    for hashed_user_id, user_data in users.items():
                        hashed_name = user_data.get('hname')
                        if hashed_name is None:
                            continue

                        if Hashing().compare(user_name, hashed_name):
                            user = user_data

                            if return_id:
                                user['hid'] = hashed_user_id

            if index == 0 and start == 'email' or index == 1:
                if user is None and user_email is not None:
                    for hashed_user_id, user_data in users.items():
                        hashed_email = user_data.get('hemail')
                        if hashed_email is None:
                            continue

                        if Hashing().compare(user_email, hashed_email):
                            user = user_data

                            if return_id:
                                user['hid'] = hashed_user_id

        if None in [password, user]:
            return user

        encrypted_user_data = user.get('data', {})
        if not isinstance(encrypted_user_data, dict) or len(encrypted_user_data) == 0:
            return user

        decryptor = SymmetricEncryption(password).decrypt

        decrypted_data = {}
        for key, value in encrypted_user_data.items():
            if key in encrypted_fields and value is not None:
                skip = False
                if decrypt_only_fields is not None:
                    if key not in decrypt_only_fields:
                        skip = True

                if not skip:
                    new_value = decryptor(value)

                    if new_value is not None:
                        value = new_value

            decrypted_data[key] = value

        user['data'] = decrypted_data
        return user

    def does_have_2fa(self, user_id: str) -> None:
        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return

        encrypted_2fa_secret = user_data.get('e2fa')
        if encrypted_2fa_secret is None:
            return False
        return True

    def add_2fa(self, user_id: str, password: str, secret: str) -> None:
        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return

        encrypted_2fa_secret = user_data.get('e2fa')
        if encrypted_2fa_secret is not None:
            return

        encrypted_secret = SymmetricEncryption(password).encrypt(secret)

        hashed_user_id, user_data = self[hashed_user_id]
        user_data['e2fa'] = encrypted_secret
        self.update(hashed_user_id, user_data)

    def get_2fa_secret(self, user_id: str, password: str) -> Optional[str]:
        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return None

        encrypted_2fa_secret = user_data.get('e2fa')
        if encrypted_2fa_secret is not None:
            return None

        decrypted_secret = SymmetricEncryption(password).decrypt(encrypted_2fa_secret)
        return decrypted_secret

    def is_password_correct(self, user_id: str, password_inp: str,
                            encrypted_fields: Optional[list] = None) -> bool:
        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return None

        hashed_password = user_data.get('hpwd')
        if hashed_password is not None:
            return Hashing(iterations = 150000).compare(password_inp, hashed_password)

        encrypted_user_data: dict = user_data.get('data')
        if None in [encrypted_fields, encrypted_user_data]:
            return False

        for key, value in encrypted_user_data.items():
            if key not in encrypted_fields:
                continue

            decrypted_value = SymmetricEncryption(password_inp).decrypt(value)
            if decrypted_value is None:
                return False
            return True

        return False

    ############################
    ### User Failed Attempts ###
    ############################

    def _clean_failed_attempts(self) -> None:
        users = self._load

        new_users = {}
        for hashed_user_id, user_data in users.items():
            failed_attempts = user_data.get('failed')
            if failed_attempts is not None:
                new_failed_attempts = []
                for failed_attempt_time in failed_attempts:
                    if int(time() - failed_attempt_time) <= 7200:
                        new_failed_attempts.append(failed_attempt_time)

                if len(new_failed_attempts) == 0:
                    del user_data['failed']
                else:
                    user_data['failed'] = new_failed_attempts

            new_users[hashed_user_id] = user_data

    def add_failed_attempt(self, user_id: str) -> None:
        self._clean_failed_attempts()

        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return

        failed_attempts: list = user_data.get('failed', [])
        failed_attempts = [time()] + failed_attempts
        failed_attempts = failed_attempts[:4]

        hashed_user_id, user_data = self[user_id]
        user_data['failed'] = failed_attempts
        self.update(hashed_user_id, user_data)

    def should_captcha_be_used(self, user_id: str) -> bool:
        self._clean_failed_attempts()

        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return

        failed_attempts: list = user_data.get('failed', [])
        return len(failed_attempts) >= 2

    ###############
    ### Session ###
    ###############

    # FIXME: Sessions must be deleted after a while

    def get_session(self, user_id: str, session_id: Optional[str] = None,
                    session_token: Optional[str] = None,
                    password: Optional[str] = None) -> Optional[dict]:
        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return None

        user_sessions: dict = user_data.get('sessions', {})

        session_data = None

        if session_id is not None:
            for hashed_session_id, stored_session_data in user_sessions.items():
                if Hashing().compare(session_id, hashed_session_id):
                    if session_token is not None:
                        hashed_session_token = stored_session_data.get('htoken')
                        if hashed_session_token is None:
                            return None

                        if not Hashing(iterations = 100000).compare(
                            session_token, hashed_session_token):
                            return None

                    session_data: dict = stored_session_data
                    break
        elif session_token is not None:
            for _, stored_session_data in user_sessions.items():
                hashed_session_token = stored_session_data.get('htoken')
                if hashed_session_token is None:
                    continue

                if Hashing(iterations = 100000).compare(session_token, hashed_session_token):
                    encrypted_session_id = stored_session_data.get('eid')
                    if encrypted_session_id is not None:
                        stored_session_data['id'] = SymmetricEncryption(session_token)\
                                                        .decrypt(encrypted_session_id)

                    session_data: dict = stored_session_data
                    break

        if None in [password, session_data]:
            return session_data

        encrypted_data = session_data.get('data', {})
        if not isinstance(encrypted_data, dict) or len(encrypted_data) == 0:
            return session_data

        decryptor = SymmetricEncryption(password).decrypt

        decrypted_data = {}
        for key, value in encrypted_data.items():
            decrypted_data[key] = decryptor(value)

        session_data['data'] = decrypted_data
        return session_data

    def create_session(self, user_id: str, password: str,
                       data: Optional[dict] = None)\
                        -> Tuple[Optional[str], Optional[str]]:
        if not isinstance(data, dict):
            data = {}

        hashed_user_id, user_data = self[user_id]
        if None in [hashed_user_id, user_data]:
            return None, None

        session = {}

        session_token = generate_random_string(14, False)
        hashed_session_token = Hashing(iterations = 100000).hash(session_token)
        session['htoken'] = hashed_session_token

        encryptor = SymmetricEncryption(password).encrypt

        encrypted_data = {}
        for key, value in data.items():
            encrypted_data[key] = encryptor(value)
        session['data'] = encrypted_data

        session_id = generate_random_string(6, False)
        while self.get_session(user_id, session_id) is not None\
            or session_id in self.reserved_session_ids:
            session_id = generate_random_string(6, False)

        self.reserved_session_ids.append(session_id)

        try:
            encrypted_session_id = SymmetricEncryption(session_token).encrypt(session_id)
            session['eid'] = encrypted_session_id

            hashed_user_id, user_data = self[hashed_user_id]
            if None in [hashed_user_id, user_data]:
                return None, None

            user_sessions: dict = user_data.get('sessions', {})

            hashed_session_id = Hashing().hash(session_id)
            while any(session_id == hashed_session_id for session_id in list(user_sessions.keys())):
                hashed_session_id = Hashing().hash(session_id)

            hashed_user_id, user_data = self[hashed_user_id]
            if None in [hashed_user_id, user_data]:
                return None, None

            user_sessions = user_data.get('sessions', {})
            user_sessions[hashed_session_id] = session
            user_data['sessions'] = user_sessions

            self.update(hashed_user_id, user_data)
            return session_id, session_token
        finally:
            self.reserved_session_ids.remove(session_id)
