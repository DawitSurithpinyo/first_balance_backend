from datetime import datetime

from pydantic import BaseModel, field_validator
from src.types.enums.responseCodes.pydanticValidate import \
    pydanticValidationResponses
from src.types.error.AppError import AppError


class partialTransaction(BaseModel, extra='forbid'):
    transactionID: str
    transactionName: str | None = None
    accountID: str | None = None
    value: int | float | None = None
    date: str | None = None
    """
        Store as ISO str in this model, but put in DB as `datetime` object.
    """
    memo: str | None = None

    @field_validator("date")
    @classmethod
    def validate_iso_date(cls, v: str):
        if v is not None:
            try:
                datetime.fromisoformat(v)
                return v
            except Exception as e:
                raise AppError(f'Error while creating updateTransactionRequest model: expect ISO format str for the "date" field when it is supplied. Details: {e}',
                               pydanticValidationResponses.ERROR_INVALID_DATE_FIELDS_FORMAT, 400)