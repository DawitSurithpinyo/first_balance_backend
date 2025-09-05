import traceback
from datetime import datetime, timezone

from flask import after_this_request, jsonify, redirect, request, session
from flask_classful import FlaskView, route
from flask_limiter import Limiter, RateLimitExceeded
from pydantic import ValidationError
from src.types.auth.DELETE import deleteAccountRequest
from src.types.auth.POST import (forgotPasswordRequest, googleLoginRequest,
                                 manualSignInRequest, manualSignUpRequest,
                                 resetPasswordRequest)
from src.types.enums.responseCodes.auth import authResponses
from src.types.error.AppError import AppError
from src.types.user.common import googleUser, normalUser
from src.usecases.authUsecase import authUsecase


class authController(FlaskView):
    def __init__(self, args: dict):
        try:
            self.authUsecase: authUsecase = args["useCase"]
            self.limiter: Limiter = args["limiter"]

            assert self.authUsecase is not None and isinstance(self.authUsecase, authUsecase)
            assert self.limiter is not None and isinstance(self.limiter, Limiter)

        except Exception as e:
            print(f"Error while constructing authController(): {e}")
            traceback.print_exc()
    
    @route("/googleLogin", methods=['POST'])
    def googleLogin(self):
        try:
            try:
                data = googleLoginRequest( **request.get_json() )
            except ValidationError as e:
                raise AppError(f'Invalid request body for api/auth/googleLogin: {e}', 
                               authResponses.googleLogin.ERROR_INVALID_REQUEST_BODY, 400)

            userCreds: googleUser = self.authUsecase.googleLogin(data=data)

            # Set custom header for CSRF token
            @after_this_request
            def addCSRFTokenHeader(response):
                response.headers["X-CSRF-Token"] = session["CSRFToken"]
                return response
            
            return jsonify({
                "success": True,
                "message": "Logged in via Google.",
                "messageCode": authResponses.googleLogin.SUCCESS,
                "data": userCreds.model_dump(exclude_none=True),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 201
        
        except Exception as e:
            print(f"Error on authController.googleLogin: ")
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
                "message": f"Unexpected internal server error on authController.googleLogin: {e}",
                "messageCode": authResponses.googleLogin.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
        
    @route("/getCredentials", methods=['GET'])
    def getCredentials(self):
        try:
            with self.limiter.limit('1 per 2 seconds'): # too strict? But refreshes usually take at least 2 seconds, and legit users would have no incentive to spam refresh
                try:
                    data, sessionDescription = self.authUsecase.retrieveCredentials()
                    @after_this_request
                    def addCSRFTokenHeader(response):
                        response.headers["X-CSRF-Token"] = session["CSRFToken"]
                        return response

                    if sessionDescription == "newPreLogin":
                        redirect('/')
                        return jsonify({
                            "success": True,
                            "message": "Created a new pre-login session with a new CSRF token.",
                            "messageCode": authResponses.getCredentials.SUCCESS_NEW_PRELOGIN_SESSION,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 201
                    
                    elif sessionDescription == "existingPreLogin":
                        redirect('/')
                        return jsonify({
                            "success": True,
                            "message": "Retrieved the CSRF token of existing pre-login session.",
                            "messageCode": authResponses.getCredentials.SUCCESS_EXISTING_PRELOGIN_SESSION,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 200
                
                    elif sessionDescription == "postLogin":
                        redirect('/dashboard')
                        return jsonify({
                            "success": True,
                            "message": "Retrieved the credentials of existing post-login session.",
                            "messageCode": authResponses.getCredentials.SUCCESS_EXISTING_POSTLOGIN_SESSION,
                            "data": data.model_dump(exclude_none=True),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 200
                    
                except RateLimitExceeded as e:
                    raise AppError(f'Route rate limit exceeded. Details: {e}',
                                authResponses.getCredentials.ERROR_RATE_LIMIT_EXCEEDED, 429)
            
        except Exception as e:
            print(f"Error on authController.getCredentials: ")
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
                "message": f"Unexpected internal server error on authController.getCredentials: {e}",
                "messageCode": authResponses.getCredentials.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
    
    @route("/signIn", methods=['POST'])
    def signIn(self):
        # What the hell is this. But I mean there is no other way to do it
        try: # any Exceptions
            with self.limiter.limit('10 per minute'):
                try: # limiter exception
                    try: # Pydantic exception
                        data = manualSignInRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError(f'Invalid request body for api/auth/signIn: {e}', 
                                    authResponses.signIn.ERROR_INVALID_REQUEST_BODY, 400)

                    result: normalUser = self.authUsecase.signIn(data=data)
                    @after_this_request
                    def addCSRFTokenHeader(response):
                        response.headers["X-CSRF-Token"] = session["CSRFToken"]
                        return response
                    
                    return jsonify({
                        "success": True,
                        "message": "Signed in.",
                        "messageCode": authResponses.signIn.SUCCESS,
                        "data": result.model_dump(exclude_none=True),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 201
                
                except RateLimitExceeded as e:
                    raise AppError(f'Route rate limit exceeded. Details: {e}',
                                   authResponses.signIn.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
        except Exception as e:
            print("Error on authController.signIn controller: ")
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
                "message": f"Unexpected internal server error on authController.signIn: {e}",
                "messageCode": authResponses.signIn.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
    
    @route("/signUp", methods=['POST'])
    def signUp(self):
        try: # any Exceptions
            with self.limiter.limit('1 per 10 seconds'):
                try: # limiter exception
                    try:
                        data = manualSignUpRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError(f'Invalid request body for api/auth/signUp: {e}',
                                    authResponses.signUp.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    token: str = self.authUsecase.signUp(data=data)
                    return jsonify({
                        "success": True,
                        "message": "Signed up with the following account activation token and an activation email sent to client.",
                        "messageCode": authResponses.signUp.SUCCESS,
                        "data": token,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 201
                
                except RateLimitExceeded as e:
                    raise AppError(f'Rate limit exceeded. Details: {e}'
                           , authResponses.signUp.ERROR_RATE_LIMIT_EXCEEDED, 429)

        except Exception as e:
            print("Error on authController.signUp: ")
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
                "message": f"Unexpected internal server error on authController.signUp: {e}",
                "messageCode": authResponses.signUp.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500

    @route("/activateAccount", methods=['POST']) 
    def activateAccount(self):
        try:
            token = request.args.get('token', default=None, type=str)
            if token is None:
                raise AppError('Expect "token" parameter on URL query string.',
                               authResponses.activateAccount.ERROR_INVALID_QUERY_STRING, 400)
            
            result: normalUser = self.authUsecase.activateAccount(token=token)
            return jsonify({
                "success": True,
                "message": "Account activated.",
                "messageCode": authResponses.activateAccount.SUCCESS,
                "data": result.model_dump(exclude_none=True),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 201
        
        except Exception as e:
            print("Error on authController.activateAccount: ")
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
                "message": f"Unexpected internal server error on authController.activateAccount: {e}",
                "messageCode": authResponses.activateAccount.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
        
    @route("/requestForgotPassword", methods=['POST'])
    def requestForgotPassword(self):
        try: # any Exceptions
            with self.limiter.limit('1 per 10 seconds'):
                try: # limiter exception
                    try:
                        data = forgotPasswordRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError(f"Invalid request body for api/auth/requestForgotPassword: {e}",
                                    authResponses.requestForgotPassword.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    token: str = self.authUsecase.requestForgotPassword(data=data)
                    return jsonify({
                        "success": True,
                        "message": "Request to reset password activated with the following token.",
                        "messageCode": authResponses.requestForgotPassword.SUCCESS,
                        "data": token,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 201
                
                except RateLimitExceeded as e:
                    raise AppError(f'Rate limit exceeded. Details: {e}'
                           , authResponses.requestForgotPassword.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
        except Exception as e:
            print("Error on authController.requestForgotPassword: ")
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
                "message": f"Unexpected internal server error on authController.requestForgotPassword: {e}",
                "messageCode": authResponses.requestForgotPassword.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500 
        
    @route("/resetPassword", methods=['POST'])
    def resetPassword(self):
        try:
            try:
                data = resetPasswordRequest( **request.get_json() )
            except ValidationError as e:
                raise AppError(f"Invalid request body for api/auth/resetPassword: {e}",
                               authResponses.resetPassword.ERROR_INVALID_REQUEST_BODY, 400)
            
            token = request.args.get("token", default = None, type = str)
            if token is None:
                raise AppError('Expect "token" parameter on the URL query string.',
                               authResponses.resetPassword.ERROR_INVALID_QUERY_STRING, 400)
            
            result: normalUser = self.authUsecase.resetPassword(data=data, token=token)
            return jsonify({
                "success": True,
                "message": "Password reset.",
                "messageCode": authResponses.resetPassword.SUCCESS,
                "data": result.model_dump(exclude_none=True),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 201

        except Exception as e:
            print("Error on authController.resetPassword: ")
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
                "message": f"Unexpected internal server error on authController.resetPassword: {e}",
                "messageCode": authResponses.resetPassword.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500 
        
    @route("/logout", methods=['POST'])
    def logout(self):
        try:
            self.authUsecase.logout()
            return jsonify({
                "success": True,
                "message": "Logged out.",
                "messageCode": authResponses.logout.SUCCESS,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200
        
        except Exception as e:
            print("Error on authController.logout: ")
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
                "message": f"Unexpected internal server error on authController.logout: {e}",
                "messageCode": authResponses.logout.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
    
    @route("/deleteAccount", methods=['DELETE'])
    def deleteAccount(self):
        try:
            try:
                data = deleteAccountRequest( **request.get_json() )
            except ValidationError as e:
                raise AppError(f'Invalid request body for api/auth/deleteAccount: {e}',
                               authResponses.deleteAccount.ERROR_INVALID_REQUEST_BODY, 400)
            
            self.authUsecase.deleteAccount(userID=data.userID)
            # redirect("/")
            return jsonify({
                "success": True,
                "message": "Account deleted.",
                "messageCode": authResponses.deleteAccount.SUCCESS,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200

        except Exception as e:
            print("Error on authController.deleteAccount: ")
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
                "message": f"Unexpected internal server error on authController.deleteAccount: {e}",
                "messageCode": authResponses.deleteAccount.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500