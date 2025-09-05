from datetime import datetime

from pydantic import BaseModel, field_validator
from src.types.enums.responseCodes.pydanticValidate import \
    pydanticValidationResponses
from src.types.error.AppError import AppError


class newTransactionData(BaseModel, extra='forbid'):
    """
        For new transaction data (no object ID yet).
    """
    transactionName: str
    accountID: str
    value: int | float
    date: str
    """
        Store as ISO str in this model, but put in DB as `datetime` object.
    """
    memo: str | None = None

    @field_validator("date")
    @classmethod
    def validate_iso_date(cls, v: str):
        try:
            datetime.fromisoformat(v)
            return v
        except Exception as e:
            raise AppError(f'Error while creating newTransactionData model: expect ISO format str for the "date" field. Details: {e}',
                           pydanticValidationResponses.ERROR_INVALID_DATE_FIELDS_FORMAT, 400)