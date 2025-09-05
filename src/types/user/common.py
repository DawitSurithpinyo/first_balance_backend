from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, field_validator
from src.types.enums.authChoice import authChoice
from src.types.error.AppError import AppError


class baseUser(BaseModel, extra='forbid'):
    userID: str
    userEmail: str
    userName: str
    lastLoginTime: datetime | None = None
    """
        Needs `datetime.now(timezone.utc)`
    """
    activatedTime: datetime | None = None
    """
        Needs `datetime.now(timezone.utc)`
    """

    @field_validator("lastLoginTime", "activatedTime")
    @classmethod
    def validateISODates(cls, v: Any):
        if v is None:
            return v
        try:
            assert isinstance(v, datetime)
            assert v.tzinfo is not None and v.utcoffset() == timedelta(0)
            v = v.replace(tzinfo=timezone.utc) # make sure client get UTC
            return v
        except Exception as e:
            raise AppError(f'Error while creating baseUser model: expect datetime.now(timezone.utc) for "lastLoginTime" and "activatedTime" fields. Details: {e}', 400)


class normalUser(baseUser, extra='forbid'):
    """
        For returning user data to client
    """
    signUpChoice: authChoice = authChoice.MANUAL
    createdTime: datetime | None = None
    """
        Needs `datetime.now(timezone.utc)`. 
        Cannot convert to isoformat `str` because we need this field as the index for `expireAfterSeconds`, which requires timezone-aware `<class 'datetime.datetime'>` object.
        .. Here is how it's used:
        
        - This field is indexed with `expireAfterSeconds` and `sparse` property.
        - User signs up, new user credentials document is created with `createdTime` field as `datetime.now(timezone.utc)`
        - MongoDB automatically deletes the document if the user doesn't activate account within 24 hours (by `expireAfterSeconds` property).
        - If the user activate account within time, this field will be deleted. Because any documents in the collection without `createdTime` field will not be affected by `expireAfterSeconds` (by `sparse` property).
        
            - Put simply, after the user activate their account, we just want the user document to live forever.
    """
    activationToken: str | None = None
    """
        Token to activate account. Used together with `createdTime` field.
    """
    resetPasswordExpireTime: datetime | None = None
    resetPasswordToken: str | None = None

    @field_validator("createdTime", "resetPasswordExpireTime")
    @classmethod
    def validateCreatedTime(cls, v: Any):
        if v is None:
            return v
        try:
            assert isinstance(v, datetime)
            assert v.tzinfo is not None and v.utcoffset() == timedelta(0)
            v = v.replace(tzinfo=timezone.utc) # make sure client get UTC
            return v
        except Exception as e:
            raise AppError(f'Error while creating normalUser model: expect datetime.now(timezone.utc) for "createdTime" and "resetPasswordExpireTime". Details: {e}', 400)


class normalUserWithPassword(normalUser, extra='forbid'):
    """
        Internal; only for methods that need to interact with user's password
    """
    hashedPassword: str


class googleUser(baseUser, extra='forbid'):
    """
        For users who sign up by Google OAuth.
        Access token, refresh token, and granted scopes depends on each sign in, so keeping in Redis server session instead of DB.
        Also because of security concerns.
    """
    signUpChoice: authChoice = authChoice.GOOGLE
    userPictureLink: str