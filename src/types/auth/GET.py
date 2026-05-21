from pydantic import BaseModel


class sessionPreLogin(BaseModel, extra='forbid'):
    CSRFToken: str

class sessionPostLogin(BaseModel, extra='forbid'):
    userID: str
    CSRFToken: str
    needTransactionsReFetch: bool