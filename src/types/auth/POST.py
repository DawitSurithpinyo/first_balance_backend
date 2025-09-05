from pydantic import BaseModel


class googleLoginRequest(BaseModel, extra='forbid'):
    code: str

class manualSignInRequest(BaseModel, extra='forbid'):
    userEmail: str
    password: str

class manualSignUpRequest(BaseModel, extra='forbid'):
    userEmail: str
    userName: str
    password: str

class forgotPasswordRequest(BaseModel, extra='forbid'):
    userEmail: str

class resetPasswordRequest(BaseModel, extra='forbid'):
    newPassword: str