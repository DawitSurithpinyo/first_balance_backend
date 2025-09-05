from typing import Any

from bson.objectid import ObjectId
from pymongo import MongoClient


class transactionRepository:
    def __init__(self, mongo: MongoClient):
        self.mongoClient = mongo
        self.userDataDB = self.mongoClient['transactionsDB']

    def getTransactions(self, userID: str) -> list[Any] | list[None]:
        col = self.userDataDB[f'{userID}']

        records = list( col.find({}) )
        return records
    
    def addTransaction(self, data: dict, userID: str, returnDocumentID: bool | None = False) -> str | None:
        """
            :param data: `dict` of type `src.types.transaction.POST.newTransactionData`.
            :param userID: Must be string.
            :param returnDocumentID: Whether to return the document ID of the inserted document as a string. Default to `False`.
        """
        col = self.userDataDB[f'{userID}']

        result = col.insert_one(data)
        if returnDocumentID:
            return str(result.inserted_id)
        
    def deleteOne(self, transactionID: ObjectId, userID: str) -> None:
        col = self.userDataDB[f'{userID}']

        col.delete_one(
            filter = {
                "_id": transactionID
            }
        )
        return
    
    def deleteMany(self, transactionIDs: list[ObjectId], userID: str, returnNumberDeleted: bool | None = False) -> int | None:
        """
            :param transactionIDs: A list of transaction IDs as `bson.objectid.ObjectId`.
            :param userID: User ID as string.
            :param returnNumberDeleted: Optional. Whether to return the number of documents deleted. Default to `False`.
        """
        col = self.userDataDB[f'{userID}']

        result = col.delete_many(
            filter = {
                {"_id": {"$in": transactionIDs} }
            }
        )

        if returnNumberDeleted:
            return result.deleted_count
        
    def updateTransaction(self, transactionID: ObjectId, userID: str, updateBody: Any) -> None:
        col = self.userDataDB[f'{userID}']

        col.update_one(
            filter = {
                "_id": transactionID
            },
            update = {
                "$set": updateBody
            }
        )

        return
    
    def deleteAll(self, userID: str) -> None:
        """
            For deleting everything when user deletes account
        """
        col = self.userDataDB[f'{userID}']

        col.delete_many()
        return

        
