from datetime import datetime

from flask import session
from pydantic import ValidationError
from src.repositories.transactionRepo import transactionRepository
from src.types.enums.responseCodes.transaction import transactionResponses
from src.types.error.AppError import AppError
from src.types.transaction.common import transactionData
from src.types.transaction.PATCH import partialTransaction
from src.types.transaction.POST import newTransactionData
from src.utils.checkSessionType import checkSessionType
from src.utils.convertStrToOID import convertStrToObjectID


class transactionUsecase:
    def __init__(self, transactionRepo: transactionRepository):
        self.transactionRepo = transactionRepo

    def getTransactions(self) -> list[dict] | list[None] | None:
        """
            If there is at least one transaction data for the given `userID` (`session['userID']`), 
            the returned list should have elements as dicts of `transactionData` structure.
        """
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('Error from transactionUsecase.getTransactions: Invalid session format, likely because user is not authenticated.',
                           transactionResponses.getAllTransactions.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        if not session['needTransactionsReFetch']:
            return None
        
        transactions: list = self.transactionRepo.getTransactions(userID = session['userID'])
        if transactions is not None and len(transactions) > 0:
            for transaction in transactions:
                transaction["transactionID"] = str(transaction.pop("_id"))
                transaction["date"] = datetime.strftime(transaction["date"], "%Y-%m-%d")
                try:
                    transaction = transactionData( **transaction )
                    transaction = transaction.model_dump()
                except ValidationError as e:
                    raise AppError(f'Error from transactionUsecase.getTransactions: Document ID {transaction["transactionID"]} returned from transactionRepository.getTransactions is invalid for type transactionData. Details: {e}',
                                   transactionResponses.getAllTransactions.ERROR_INVALID_GET_FROM_DB, 500)
                
        session['needTransactionsReFetch'] = False

        return transactions
    
    def addTransaction(self, data: newTransactionData) -> str:
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('Error from transactionUsecase.addTransaction: Invalid session format, likely because user is not authenticated.',
                           transactionResponses.addTransaction.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        d = data.model_dump()
        d['date'] = datetime.fromisoformat(d['date'])
        
        insertedID: str = self.transactionRepo.addTransaction(data=d, userID=session['userID'], returnDocumentID=True)
        session['needTransactionsReFetch'] = True

        return insertedID
    
    def deleteOne(self, transactionID: str) -> None:
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('Error from transactionUsecase.deleteOne: Invalid session format, likely because user is not authenticated.',
                           transactionResponses.deleteOne.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        transactionID = convertStrToObjectID(field=transactionID, fieldName='transactionID', originFuncName='transactionUsecase.deleteOne')
        self.transactionRepo.deleteOne(transactionID=transactionID, userID=session['userID'])

        session['needTransactionsReFetch'] = True

    def deleteMany(self, transactionIDs: list[str]) -> int:
        """
            Return number of documents deleted.
        """
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('Error from transactionUsecase.deleteMany: Invalid session format, likely because user is not authenticated.',
                           transactionResponses.deleteMany.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        if len(transactionIDs) > 0:
            IDs = [ convertStrToObjectID(field=id, fieldName="transactionID", 
                    originFuncName="transactionUsecase.deleteMany") for id in transactionIDs ]
                
            numberDeleted: int = self.transactionRepo.deleteMany(transactionIDs=IDs, userID=session['userID'], returnNumberDeleted=True)
            session['needTransactionsReFetch'] = True
            return numberDeleted
        
        return 0 # If list empty (no documents to delete), don't bother making round trip to DB
    
    def updateTransaction(self, transaction: partialTransaction) -> bool:
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('Error from transactionUsecase.updateTransaction: Invalid session format, likely because user is not authenticated.',
                           transactionResponses.update.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        check = transaction.model_dump()
        toUpdate: dict = {}
        for k, v in check.items():
            if v is not None or k == "memo": # "memo" = None is a valid update
                toUpdate[k] = v
        if len(toUpdate) <= 1 and 'transactionID' in toUpdate.keys():
            # Avoid making round trip to DB if the request body only contains transactionID (nothing to update)
            return False

        transacID = convertStrToObjectID(field=toUpdate['transactionID'], fieldName='transactionID', 
                                         originFuncName='transactionUsecase.updateTransaction')
        del toUpdate['transactionID']
        if 'date' in toUpdate.keys():
            toUpdate['date'] = datetime.fromisoformat(toUpdate['date'])
        
        self.transactionRepo.updateTransaction(transactionID=transacID, userID=session['userID'], updateBody=toUpdate)
        session['needTransactionsReFetch'] = True
        return True