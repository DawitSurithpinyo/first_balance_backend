from pydantic import BaseModel


class deleteAccountRequest(BaseModel, extra='forbid'):
    userID: str