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

            if self.authUsecase is None or not isinstance(self.authUsecase, authUsecase):
                raise Exception("authUsecase object is not provided, or not of correct type")
            if self.limiter is None or not isinstance(self.limiter, Limiter):
                raise Exception("limiter is not provided, or not of type flask_limiter.Limiter")

        except Exception as e:
            print(f"Error while constructing authController(): {e}")
            traceback.print_exc()
    
    @route("/googleLogin", methods=['POST'])
    def googleLogin(self):
        try: 
            with self.limiter.limit('1 per 5 seconds'):
                try:
                    try:
                        data = googleLoginRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError('Invalid request body', 
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
                    }), 200
                
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                authResponses.googleLogin.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
        except Exception as e:
            print("Error on authController.googleLogin: ")
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
                "message": "Internal server error",
                "messageCode": authResponses.googleLogin.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
        
    @route("/getCredentials", methods=['GET'])
    def getCredentials(self):
        try:
            with self.limiter.limit('3 per 1 second'):
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
                            "message": "Created a new pre-login session.",
                            "messageCode": authResponses.getCredentials.SUCCESS_NEW_PRELOGIN_SESSION,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 201
                    
                    elif sessionDescription == "existingPreLogin":
                        redirect('/')
                        return jsonify({
                            "success": True,
                            "message": "Retrieved the existing pre-login session.",
                            "messageCode": authResponses.getCredentials.SUCCESS_EXISTING_PRELOGIN_SESSION,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 200
                
                    elif sessionDescription == "postLogin":
                        redirect('/dashboard')
                        return jsonify({
                            "success": True,
                            "message": "Retrieved the existing post-login session.",
                            "messageCode": authResponses.getCredentials.SUCCESS_EXISTING_POSTLOGIN_SESSION,
                            "data": data.model_dump(exclude_none=True),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }), 200
                    
                except RateLimitExceeded:
                    raise AppError('Route rate limit exceeded.',
                                authResponses.getCredentials.ERROR_RATE_LIMIT_EXCEEDED, 429)
            
        except Exception as e:
            print("Error on authController.getCredentials: ")
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
                "message": "Internal server error",
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
                        raise AppError('Invalid request body', 
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
                    raise AppError('Route rate limit exceeded',
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
                "message": "Internal server error",
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
                        raise AppError('Invalid request body',
                                    authResponses.signUp.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    self.authUsecase.signUp(data=data)
                    return jsonify({
                        "success": True,
                        "message": "Signed up with an activation email sent to client.",
                        "messageCode": authResponses.signUp.SUCCESS,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 201
                
                except RateLimitExceeded as e:
                    raise AppError('Rate limit exceeded'
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
                "message": "Internal server error",
                "messageCode": authResponses.signUp.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500

    @route("/activateAccount", methods=['POST']) 
    def activateAccount(self):
        try:
            with self.limiter.limit('1 per 5 seconds'):
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
                
                except RateLimitExceeded as e:
                    raise AppError('Rate limit exceeded'
                        , authResponses.activateAccount.ERROR_RATE_LIMIT_EXCEEDED, 429)
        
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
                "message": "Internal server error",
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
                        raise AppError("Invalid request body",
                                    authResponses.requestForgotPassword.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    # WHY do I need to return token to the client when an email is sent to them??
                    # Wtf was I thinking????
                    token: str = self.authUsecase.requestForgotPassword(data=data)
                    return jsonify({
                        "success": True,
                        "message": "Request to reset password activated with the following token.",
                        "messageCode": authResponses.requestForgotPassword.SUCCESS,
                        "data": token,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 201
                
                except RateLimitExceeded as e:
                    raise AppError('Rate limit exceeded'
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
                "message": "Internal server error",
                "messageCode": authResponses.requestForgotPassword.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500 
        
    @route("/resetPassword", methods=['POST'])
    def resetPassword(self):
        try:
            with self.limiter.limit('1 per 5 seconds'):
                try:
                    try:
                        data = resetPasswordRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError("Invalid request body",
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
                
                except RateLimitExceeded as e:
                    raise AppError('Rate limit exceeded'
                           , authResponses.resetPassword.ERROR_RATE_LIMIT_EXCEEDED, 429)

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
                "message": "Internal server error",
                "messageCode": authResponses.resetPassword.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500 
        
    @route("/logout", methods=['POST'])
    def logout(self):
        try:
            with self.limiter.limit('1 per 5 seconds'):
                try:
                    self.authUsecase.logout()
                    return jsonify({
                        "success": True,
                        "message": "Logged out.",
                        "messageCode": authResponses.logout.SUCCESS,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 200
                
                except RateLimitExceeded as e:
                    raise AppError('Rate limit exceeded'
                           , authResponses.logout.ERROR_RATE_LIMIT_EXCEEDED, 429)                
        
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
                "message": "Internal server error",
                "messageCode": authResponses.logout.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
    
    @route("/deleteAccount", methods=['DELETE'])
    def deleteAccount(self):
        try:
            with self.limiter.limit('1 per 10 seconds'):
                try:
                    try:
                        data = deleteAccountRequest( **request.get_json() )
                    except ValidationError as e:
                        raise AppError('Invalid request body',
                                    authResponses.deleteAccount.ERROR_INVALID_REQUEST_BODY, 400)
                    
                    self.authUsecase.deleteAccount(userID=data.userID)
                    # redirect("/")
                    return jsonify({
                        "success": True,
                        "message": "Account deleted.",
                        "messageCode": authResponses.deleteAccount.SUCCESS,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }), 200
                
                except RateLimitExceeded as e:
                    raise AppError('Rate limit exceeded'
                           , authResponses.deleteAccount.ERROR_RATE_LIMIT_EXCEEDED, 429)

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
                "message": "Internal server error",
                "messageCode": authResponses.deleteAccount.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500