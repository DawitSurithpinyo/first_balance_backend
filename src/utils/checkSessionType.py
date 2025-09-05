from pydantic import ValidationError
from src.types.auth.GET import sessionPostLogin, sessionPreLogin


def checkSessionType(sessionDict: dict):
    # Don't consider hidden fields automagically created by flask_session (ones starting with underscore)
    temp: dict = {}
    for k, v in sessionDict.items():
        if k[0] != "_":
            temp[k] = v

    try:
        sessionPreLogin.model_validate(temp, strict=True)
        return "preLogin"
    except ValidationError:
        pass

    try:
        sessionPostLogin.model_validate(temp, strict=True)
        return "postLogin"
    except ValidationError:
        pass

    return "unknown"