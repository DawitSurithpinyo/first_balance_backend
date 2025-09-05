from types.error.AppError import AppError

import requests


def verifyGoogleOAuthToken(token: str):
    try:
        resp = requests.get(
            url = f'https://oauth2.googleapis.com/tokeninfo?id_token={token}',
            timeout = 10
        )
    except Exception as e:
        raise AppError('blah', 401)