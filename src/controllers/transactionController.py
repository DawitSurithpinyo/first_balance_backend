import traceback
from datetime import datetime, timezone

from flask import jsonify, request, session, current_app
from infrastructure.http.response import sendError
from flask_classful import FlaskView, route
from flask_limiter import Limiter, RateLimitExceeded
from pydantic import ValidationError
from src.types.enums.responseCodes.transaction import transactionResponses
from src.types.error.AppError import AppError
from src.types.transaction.DELETE import (deleteManyTransactionsRequest,
                                          deleteOneTransactionRequest)
from src.types.transaction.PATCH import partialTransaction
from src.types.transaction.POST import newTransactionData, createNewTransactionResponse
from src.usecases.transactionUsecase import transactionUsecase


class transactionController(FlaskView):
    def __init__(self, args: dict):
        try:
            useCase: transactionUsecase = args["useCase"]
            limiter: Limiter = args["limiter"]

            if useCase is None or not isinstance(useCase, transactionUsecase):
                raise Exception("useCase is not provided, or not of correct type")
            if limiter is None or not isinstance(limiter, Limiter):
                raise Exception("limiter is not provided, or not of correct type")

            self.transactionUsecase = useCase
            self.limiter = limiter

        except Exception as e:
            print(f"Error while constructing transactionController(): {e}")
            traceback.print_exc()

    @route("/get", methods=['GET'])
    def getAllTransactions(self):
        try:
            with self.limiter.limit('5 per 1 second', key_func=lambda: session.sid):
                try:
                    transactions: list | None = self.transactionUsecase.getTransactions()
                    if transactions is None:
                        return jsonify({
                            "success": True,
                            "message": "User's transactions data is up to date, no re-fetching is needed.",
                            "messageCode": transactionResponses.getAllTransactions.SUCCESS_NO_REFETCH_NEEDED,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 200

                    return jsonify({
                        "success": True,
                        "message": "Retrieved user's transaction data.",
                        "messageCode": transactionResponses.getAllTransactions.SUCCESS_FETCHED,
                        "data": transactions,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 200
        
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                transactionResponses.getAllTransactions.ERROR_RATE_LIMIT_EXCEEDED, 429)

        except Exception as e:
            with current_app.app_context():
                return sendError(e)
        
    @route("/add", methods=['POST'])
    def addTransaction(self):
        try:
            with self.limiter.limit('1 per 1 second', key_func=lambda: session.sid):
                try:
                    try:
                        data = newTransactionData( **request.get_json() )
                    except ValidationError as e:
                        raise AppError('Invalid request body',
                                    transactionResponses.addTransaction.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    res: createNewTransactionResponse = self.transactionUsecase.addTransaction(data=data)
                    return jsonify({
                        "success": True,
                        "message": "Inserted",
                        "messageCode": transactionResponses.addTransaction.SUCCESS,
                        "data": res.model_dump(),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 201
                
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                transactionResponses.addTransaction.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
        except Exception as e:
            with current_app.app_context():
                return sendError(e)

    @route("/deleteOne", methods=['DELETE']) 
    def deleteOne(self):
        try:
            with self.limiter.limit('5 per 1 second', key_func=lambda: session.sid):
                try:
                    try:
                        data = deleteOneTransactionRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError('Invalid request body',
                                    transactionResponses.deleteOne.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    self.transactionUsecase.deleteOne(transactionID=data.transactionID)
                    return jsonify({
                        "success": True,
                        "message": "Deleted.",
                        "messageCode": transactionResponses.deleteOne.SUCCESS,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 200
                
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                transactionResponses.deleteOne.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
        except Exception as e:
            with current_app.app_context():
                return sendError(e)
    
    @route("/deleteMany", methods=['DELETE']) 
    def deleteMany(self):
        try:
            with self.limiter.limit('2 per 1 second', key_func=lambda: session.sid):
                try:
                    try:
                        data = deleteManyTransactionsRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError('Invalid request body',
                                    transactionResponses.deleteMany.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    numberDeleted = self.transactionUsecase.deleteMany(transactionIDs=data.transactionIDsList)
                    return jsonify({
                        "success": True,
                        "message": f"Deleted {numberDeleted} transactions.",
                        "messageCode": transactionResponses.deleteMany.SUCCESS,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 200
                
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                transactionResponses.deleteMany.ERROR_RATE_LIMIT_EXCEEDED, 429)
                
        except Exception as e:
            with current_app.app_context():
                return sendError(e)
        
    @route("/update", methods=['PATCH']) 
    def update(self):
        try:
            with self.limiter.limit('5 per 1 second', key_func=lambda: session.sid):
                try:
                    try:
                        data = partialTransaction( **request.get_json() )
                    except ValidationError as e:
                        raise AppError('Invalid request body',
                                    transactionResponses.update.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    updated: bool = self.transactionUsecase.updateTransaction(transaction=data)
                    if not updated:
                        return jsonify({
                            "success": True,
                            "message": "Only transactionID is provided, no update was made.",
                            "messageCode": transactionResponses.update.SUCCESS_NO_UPDATE,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 200
                    return jsonify({
                        "success": True,
                        "message": "Updated.",
                        "messageCode": transactionResponses.update.SUCCESS_UPDATED,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 200
                
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                transactionResponses.update.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
        except Exception as e:
            with current_app.app_context():
                return sendError(e)