from datetime import datetime

from pydantic import BaseModel


class sessionPreLogin(BaseModel, extra='forbid'):
    CSRFToken: str

class sessionPostLogin(BaseModel, extra='forbid'):
    userID: str
    CSRFToken: str
    needTransactionsReFetch: bool
    accessToken: str | None = None # Only for Google user
    refreshToken: str | None = None # Only for Google user
    grantedScopes: list[str] | None = None # Only for Google user