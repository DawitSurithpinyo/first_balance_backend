import traceback
from datetime import datetime, timezone

from flask import jsonify, request
from flask_classful import FlaskView, route
from pydantic import ValidationError
from src.types.enums.responseCodes.transaction import transactionResponses
from src.types.error.AppError import AppError
from src.types.transaction.DELETE import (deleteManyTransactionsRequest,
                                          deleteOneTransactionRequest)
from src.types.transaction.PATCH import partialTransaction
from src.types.transaction.POST import newTransactionData
from src.usecases.transactionUsecase import transactionUsecase


class transactionController(FlaskView):
    def __init__(self, useCase: transactionUsecase):
        self.transactionUsecase = useCase

    @route("/get", methods=['GET'])
    def getAllTransactions(self):
        try:
            transactions: list | None = self.transactionUsecase.getTransactions()
            if transactions is None:
                # 304 Not modified doesn't send any response body, so there's actually no need to make the response body
                # But I want to put it for clarity.
                return jsonify({
                    "success": True,
                    "message": "User's transactions data is up to date, no re-fetching is needed.",
                    "messageCode": transactionResponses.getAllTransactions.SUCCESS_NO_REFETCH_NEEDED,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), 304

            return jsonify({
                "success": True,
                "message": "Retrieved user's data.",
                "messageCode": transactionResponses.getAllTransactions.SUCCESS_FETCHED,
                "data": transactions,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        except Exception as e:
            print("Error on transactionController.getAllTransactions: ")
            traceback.print_exc()
            if isinstance(e, AppError):
                return jsonify({
                    "success": False,
                    "message": e.message,
                    "messageCode": e.messageCode,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), e.statusCode
            return jsonify({
                "success": False,
                "message": f"Unexpected internal server error on transactionController.getAllTransactions: {e}",
                "messageCode": transactionResponses.getAllTransactions.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
        
    @route("/add", methods=['POST'])
    def addTransaction(self):
        try:
            try:
                data = newTransactionData( **request.get_json() )
            except ValidationError as e:
                raise AppError(f'Invalid request body for api/transaction/add: {e}',
                               transactionResponses.addTransaction.ERROR_INVALID_REQUEST_BODY, 400)
            
            insertedID: str = self.transactionUsecase.addTransaction(data=data)
            return jsonify({
                "success": True,
                "message": f"Inserted a transaction with ID {insertedID}.",
                "messageCode": transactionResponses.addTransaction.SUCCESS,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 201
        
        except Exception as e:
            print("Error on transactionController.addTransaction: ")
            traceback.print_exc()
            if isinstance(e, AppError):
                return jsonify({
                    "success": False,
                    "message": e.message,
                    "messageCode": e.messageCode,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), e.statusCode
            return jsonify({
                "success": False,
                "message": f"Unexpected internal server error on transactionController.addTransaction: {e}",
                "messageCode": transactionResponses.addTransaction.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500

    @route("/deleteOne", methods=['DELETE']) 
    def deleteOne(self):
        try:
            try:
                data = deleteOneTransactionRequest( **request.get_json() )
            except ValidationError as e:
                raise AppError(f'Invalid request body for api/transaction/deleteOne: {e}',
                               transactionResponses.deleteOne.ERROR_INVALID_REQUEST_BODY, 400)
            
            self.transactionUsecase.deleteOne(transactionID=data.transactionID)
            return jsonify({
                "success": True,
                "message": f"Deleted a transaction with object ID {data.transactionID}.",
                "messageCode": transactionResponses.deleteOne.SUCCESS,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        
        except Exception as e:
            print("Error on transactionController.deleteOne: ")
            traceback.print_exc()
            if isinstance(e, AppError):
                return jsonify({
                    "success": False,
                    "message": e.message,
                    "messageCode": e.messageCode,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), e.statusCode
            return jsonify({
                "success": False,
                "message": f"Unexpected internal server error on transactionController.deleteOne: {e}",
                "messageCode": transactionResponses.deleteOne.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
    
    @route("/deleteMany", methods=['DELETE']) 
    def deleteMany(self):
        try:
            try:
                data = deleteManyTransactionsRequest( **request.get_json() )
            except ValidationError as e:
                raise AppError(f'Invalid request body for api/transaction/deleteMany: {e}',
                               transactionResponses.deleteMany.ERROR_INVALID_REQUEST_BODY, 400)
            
            numberDeleted = self.transactionUsecase.deleteMany(transactionIDs=data.transactionIDsList)
            return jsonify({
                "success": True,
                "message": f"Deleted {numberDeleted} transactions.",
                "messageCode": transactionResponses.deleteMany.SUCCESS,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        except Exception as e:
            print("Error on transactionController.deleteMany: ")
            traceback.print_exc()
            if isinstance(e, AppError):
                return jsonify({
                    "success": False,
                    "message": e.message,
                    "messageCode": e.messageCode,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), e.statusCode
            return jsonify({
                "success": False,
                "message": f"Unexpected internal server error on transactionController.deleteMany: {e}",
                "messageCode": transactionResponses.deleteMany.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500      
        
    @route("/update", methods=['PATCH']) 
    def update(self):
        try:
            try:
                data = partialTransaction( **request.get_json() )
            except ValidationError as e:
                raise AppError(f'Invalid request body for api/transaction/update: {e}',
                               transactionResponses.update.ERROR_INVALID_REQUEST_BODY, 400)
            
            updated = self.transactionUsecase.updateTransaction(transaction=data)
            if not updated:
                return jsonify({
                    "success": True,
                    "message": "Only transactionID is provided, no update is made.",
                    "messageCode": transactionResponses.update.SUCCESS_NO_UPDATE,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), 200
            return jsonify({
                "success": True,
                "message": "Updated a transaction.",
                "messageCode": transactionResponses.update.SUCCESS_UPDATED,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        
        except Exception as e:
            print("Error on transactionController.update: ")
            traceback.print_exc()
            if isinstance(e, AppError):
                return jsonify({
                    "success": False,
                    "message": e.message,
                    "messageCode": e.messageCode,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }), e.statusCode
            return jsonify({
                "success": False,
                "message": f"Unexpected internal server error on transactionController.update: {e}",
                "messageCode": transactionResponses.update.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500    