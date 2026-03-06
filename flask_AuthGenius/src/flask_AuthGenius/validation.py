from typing import Tuple, Optional
from werkzeug import Request
from .auth import UserSystem
from .utils import WebPage, Captcha, SymmetricData, TOTP, get_url_from_request, remove_args_from_url

class Validation:
    """
    This class provides methods for validating user login credentials.
    """

    @staticmethod
    def validate_login(request: Request, user_system: UserSystem,
                       captcha: Captcha, use_captchas: bool = True)\
                        -> Tuple[Optional[dict], Optional[dict]]:
        """
        Validate user login credentials and process captcha if required.

        :param request: The HTTP request object.
        :param user_system: The user system managing user data.
        :param captcha: The captcha verification object.
        :param use_captchas: Flag indicating whether to use captchas.
        :return: A dictionary containing response data or None if login is successful.
        """

        data = request.form
        if request.is_json and request.method.lower() == 'post':
            data = request.get_json()

        name = data.get('name')
        password = data.get('password')
        captcha_code = data.get('captcha_code')
        captcha_secret = data.get('captcha_secret')

        stay = data.get('stay', '0')
        stay = '1' if stay == '1' else '0'

        response = {"error": None, "error_fields": [], "content": {}}

        language = WebPage.client_language(request, 'en')

        if not name or not password:
            response['error'] = WebPage.translate_text(
                'Please fill in all fields.', 'en', language
            )
            error_fields = []
            if name is None and not password is None:
                error_fields.append('name')
            elif password is None and not name is None:
                error_fields.append('password')
            response['error_fields'] = error_fields
            return response, None

        user = user_system.get_user(
            user_name = name, user_email = name,
            password = password, return_id = True,
            decrypt_only_fields = ['id']
        )

        print(user)
        if user is None:
            response['error'] = WebPage.translate_text(
                'The username / email was not found.', 'en', language
            )
            response['error_fields'] = ['name']
            return response, user

        user_id = user.get('hid') if user.get('id') is None else user.get('id')

        if use_captchas and user_system.should_captcha_be_used(user_id):
            failed_captcha = False
            if not captcha_code or not captcha_secret:
                response['error'] = WebPage.translate_text(
                    'Please solve the captcha.', 'en', language
                )
                failed_captcha = True
            else:
                error_reason = captcha.verify(
                    captcha_code, captcha_secret,
                    {'name': name, 'password': password}
                )

                if error_reason == 'code':
                    response['error'] = WebPage.translate_text(
                        'The captcha was not correct, try again.', 'en', language
                    )
                    failed_captcha = True
                elif error_reason == 'data':
                    response['error'] = WebPage.translate_text(
                        'Data has changed, re-enter the captcha.', 'en', language
                    )
                    failed_captcha = True
                elif error_reason == 'time':
                    response['error'] = WebPage.translate_text(
                        'The captcha has expired, try again.', 'en', language
                    )
                    failed_captcha = True

            if failed_captcha:
                response['error_fields'] = ['captcha']

                captcha_img, captcha_secret = captcha.generate(
                    {'name': name, 'password': password}
                )

                response['content']['captcha_img'] = captcha_img
                response['content']['captcha_secret'] = captcha_secret
                return response, user

        if not user_system.is_password_correct(user_id, password):
            user_system.add_failed_attempt(user_id)

            response['error'] = WebPage.translate_text(
                'The password is not correct.', 'en', language
            )
            response['error_fields'] = ['password']
            return response, user

        return None, user

    @staticmethod
    def validate_login_2fa(request: Request, user_system: UserSystem,
                           captcha: Captcha, encryptor: SymmetricData,
                           totp: TOTP, use_captchas: bool = True)\
                            -> Tuple[Optional[dict], Optional[dict]]:
        data = request.form
        if request.is_json and request.method.lower() == 'post':
            data = request.get_json()

        user_data = data.get('data')
        totp_code = data.get('totp')
        captcha_code = data.get('captcha_code')
        captcha_secret = data.get('captcha_secret')

        response = {"error": None, "error_fields": [], "content": {}}

        language = WebPage.client_language(request, 'en')

        if not user_data or not totp_code:
            response['error'] = WebPage.translate_text(
                'Please fill in all fields.', 'en', language
            )
            return response, None

        user = None
        decrypted_data = encryptor.decode(user_data)
        if decrypted_data is not None:
            user_name = decrypted_data['name']
            user = user_system.get_user(
                user_name = user_name, user_email = user_name,
                password = decrypted_data['password'],
                decrypt_only_fields = ['id'], return_id = True
            )

        if None in [decrypted_data, user]:
            current_url = get_url_from_request(request)
            current_url_without_args = remove_args_from_url(current_url)
            current_args = current_url.replace(current_url_without_args, "")

            response['content']['redirection_url'] = '/login' + current_args
            return response, None

        language = WebPage.client_language(request, 'en')

        user_id = user['data']['id']

        if not user_system.does_have_2fa(user_id):
            return None, user

        if use_captchas and user_system.should_captcha_be_used(user_id):
            failed_captcha = False
            if not captcha_code or not captcha_secret:
                response['error'] = WebPage.translate_text(
                    'Please solve the captcha.', 'en', language
                )
                failed_captcha = True
            else:
                error_reason = captcha.verify(
                    captcha_code, captcha_secret,
                    {'dec_data': decrypted_data, 'totp': totp_code}
                )

                if error_reason == 'code':
                    response['error'] = WebPage.translate_text(
                        'The captcha was not correct, try again.', 'en', language
                    )
                    failed_captcha = True
                elif error_reason == 'data':
                    response['error'] = WebPage.translate_text(
                        'Data has changed, re-enter the captcha.', 'en', language
                    )
                    failed_captcha = True
                elif error_reason == 'time':
                    response['error'] = WebPage.translate_text(
                        'The captcha has expired, try again.', 'en', language
                    )
                    failed_captcha = True
            if failed_captcha:
                response['error_fields'] = ['captcha']

                captcha_img, captcha_secret = captcha.generate(
                    {'dec_data': decrypted_data, 'totp': totp_code}
                )

                response['content']['captcha_img'] = captcha_img
                response['content']['captcha_secret'] = captcha_secret
                return response

        secret = user_system.get_2fa_secret(user_id, decrypted_data['password'])
        if secret is None:
            return None, user

        if not totp.verify(totp_code, secret):
            user_system.add_failed_attempt(user_id)

            response['error'] = WebPage.translate_text(
                'The code entered is incorrect.', 'en', language
            )
            return response, user

        return None, user
