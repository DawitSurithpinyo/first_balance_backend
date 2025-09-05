from src.types.transaction.POST import newTransactionData


class transactionData(newTransactionData, extra='forbid'):
    """
        For transaction data already created in DB (already has object ID).
    """
    transactionID: str