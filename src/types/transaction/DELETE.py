from pydantic import BaseModel


class deleteOneTransactionRequest(BaseModel, extra='forbid'):
    transactionID: str

class deleteManyTransactionsRequest(BaseModel, extra='forbid'):
    transactionIDsList: list[str]