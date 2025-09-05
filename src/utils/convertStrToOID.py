from bson.errors import InvalidId
from bson.objectid import ObjectId
from src.types.error.AppError import AppError


def convertStrToObjectID(field: str, fieldName: str, originFuncName: str | None = None, useAppError: bool | None = True) -> ObjectId:
    """
        Convert value of `field` argument from `str` to `bson.objectid.ObjectId`.

        :param field: A field to convert its value from `str` to `bson.objectid.ObjectId`.
        :param fieldName: The name of wanted field. Only for making error message descriptive.
        :param originFuncName: Optional. Only for including the origin function name (that call this function) in error message for clarity.
        :param useAppError: Optional. Whether to use `src.types.error.AppError.AppError` with HTTP status code `400` for raising exception if conversion fail. Default to `True`.
    """
    if isinstance(field, ObjectId):
        return field
    
    try:
        converted = ObjectId(field)
    except InvalidId:
        if originFuncName is None and (useAppError is None or useAppError):
            raise AppError(f'Invalid {fieldName} format.', 400)
        elif originFuncName is not None and (useAppError is None or useAppError):
            raise AppError(f'Error from {originFuncName}: invalid {fieldName} format.', 400)
        elif originFuncName is None and not useAppError:
            raise Exception(f'Invalid {fieldName} format.')
        else:
            raise Exception(f'Error from {originFuncName}: invalid {fieldName} format.')
        
    return converted