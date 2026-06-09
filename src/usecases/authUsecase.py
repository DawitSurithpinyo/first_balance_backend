import secrets
import traceback
from datetime import datetime, timedelta, timezone
from typing import Literal

import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests
from argon2 import PasswordHasher, exceptions
from config.googleOAuthConfig import (CLIENT_SECRETS_FILE, 
                                      CLIENT_ID,
                                      SCOPES)
from flask import current_app, request, session
from pydantic import ValidationError
from redis import Redis
from src.repositories.transactionRepo import transactionRepository
from src.repositories.userRepo import userRepository
from src.types.auth.GET import sessionPostLogin, sessionPreLogin
from src.types.auth.POST import (forgotPasswordRequest, googleLoginRequest,
                                 manualSignInRequest, manualSignUpRequest,
                                 resetPasswordRequest)
from src.types.enums.authChoice import authChoice
from src.types.enums.responseCodes.auth import authResponses
from src.types.error.AppError import AppError
from src.types.user.common import (googleUser, normalUser)
from src.utils.checkSessionType import checkSessionType
from src.utils.convertStrToOID import convertStrToObjectID
from src.utils.sendEmail import sendEmail
from config.flaskConfig import *


class authUsecase():
    def __init__(self, 
                 userRepo: userRepository,
                 transactionRepo: transactionRepository,
                 pwHasher: PasswordHasher,
                 conf: DevConfig | ProdConfig):
        try:
            if userRepo is None or not isinstance(userRepo, userRepository):
                raise Exception("userRepo argument is not provided, or is not of correct type")
            if transactionRepo is None or not isinstance(transactionRepo, transactionRepository):
                raise Exception("transactionRepo argument is not provided, or is not of correct type")
            if pwHasher is None or not isinstance(pwHasher, PasswordHasher):
                raise Exception("pwHasher argument is not provided, or is not of correct type")
            if conf is None or not isinstance(conf, (DevConfig, ProdConfig)):
                raise Exception("conf argument is not provided, or is not of one of the valid types")

            self.userRepo = userRepo
            self.transactionRepo = transactionRepo
            self.passwordHasher = pwHasher
            self.config = conf

        except Exception as e:
            print(f"Error constructing authUsecase: {e}")
            traceback.print_exc()


    def googleLogin(self, data: googleLoginRequest) -> googleUser:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=request.headers.get('X-CSRF-Token', type = str)
        )
        flow.redirect_uri = 'postmessage'

        # Exchange authorization code for ID Token
        flow.fetch_token(code=data.code)
        flowCreds = flow.credentials

        # Verify ID Token
        idTokenClaim = id_token.verify_oauth2_token(flowCreds.id_token, requests.Request(), CLIENT_ID)
        if idTokenClaim["aud"] != CLIENT_ID:
            raise AppError("Internal server error",
                           authResponses.googleLogin.INTERNAL_SERVER_ERROR_INVALID_CLIENT_ID, 500)
        if not idTokenClaim["email_verified"]:
            raise AppError("Google email not verified.",
                           authResponses.googleLogin.ERROR_UNVERIFIED_GOOGLE_EMAIL, 400)

        user = {
            "userEmail": idTokenClaim['email'],
            "userName": idTokenClaim['name'],
            "userPictureLink": idTokenClaim['picture']
            # Intentionally not storing idTokenClaim["sub"] here, I didn't make proper separation between internal models and DTOs
            # And to change schema now is kind of disastrous
            # aauuughgghhhhhhhhhhhhh
        }
        
        # Check if user with this email already exists
        # If not, make sure to activate their account
        exists = self.userRepo.getUserCredentials(filter = {"userEmail": idTokenClaim['email']})

        if exists is not None and exists['signUpChoice'] == authChoice.MANUAL:
            raise AppError('User cannot login via Google OAuth, as their first sign up was done via manual sign up method.',
                           authResponses.googleLogin.ERROR_INVALID_LOGIN_METHOD, 400)
        
        if exists is None:
            user['signUpChoice'] = authChoice.GOOGLE
            user['activatedTime'] = datetime.now(timezone.utc)

        user['lastLoginTime'] = datetime.now(timezone.utc)

        try:
            result = self.userRepo.patchUserCredentials(user, 
                        filter = {"userEmail": idTokenClaim['email']})
            result['userID'] = str(result.pop('_id'))
            result = googleUser( **result )
        except ValidationError:
            raise AppError("Internal server error",
                           authResponses.googleLogin.ERROR_INVALID_RESULT_FROM_DB, 500)
        
        session.clear() # Clear pre-login session
        session.update( sessionPostLogin( **{
            "userID": result.userID,
            "CSRFToken": secrets.token_urlsafe(128),
            "needTransactionsReFetch": True,
        } ).model_dump(exclude_none=True) )
        current_app.session_interface.regenerate(session) # regenerate session ID

        return result

    def retrieveCredentials(self) -> \
        tuple[None, Literal["newPreLogin"]] | \
        tuple[None, Literal["existingPreLogin"]] | \
        tuple[normalUser | googleUser, Literal["postLogin"]]:

        sessionType = checkSessionType(dict(session))
        if sessionType == "unknown":
            # This is user's first time visiting, or their cookies and session has expired
            # They will need to log in
            data = sessionPreLogin( **{
                "CSRFToken": secrets.token_urlsafe(128)
            } )
            session.update(data.model_dump())
            return None, "newPreLogin"
        
        elif sessionType == "preLogin":
            # User is not authenticated yet, but has already received the pre-login CSRFToken
            # This is for when user refreshes the page and lost in-memory CSRF token
            # So we will just send back the CSRF token via header
            return None, "existingPreLogin"
        
        elif sessionType == "postLogin":
            # We need to be able fetch user's transaction data when login is completed, regardless of the last request on transaction made by the user before logging out.
            session['needTransactionsReFetch'] = True

            # Also send back their credentials, because they are wiped out if refreshed/tab closed too
            id = convertStrToObjectID(field=session['userID'], fieldName='userID', originFuncName='authUsecase.retrieveCredentials')
            result: dict = self.userRepo.getUserCredentials(
                filter = {"_id": id},
                projection = {'activationToken': False, 
                              'resetPasswordExpireTime': False, 'resetPasswordToken': False}
            )
            result['userID'] = str(result.pop('_id'))
            
            try:
                if result['signUpChoice'] == authChoice.GOOGLE:
                    res = googleUser( **result )
                    return res, "postLogin"
                elif result['signUpChoice'] == authChoice.MANUAL:
                    res = normalUser( **result )
                    return res, "postLogin"
            except ValidationError:
                raise AppError("Internal server error",
                               authResponses.getCredentials.ERROR_INVALID_DB_RESULT_FOR_POSTLOGIN, 500)
        
        raise AppError("Internal server error",
                       authResponses.getCredentials.ERROR_MALFORMED_SERVER_SESSION, 500)

    def signIn(self, data: manualSignInRequest) -> normalUser:
        # Check error cases
        try:
            user = self.userRepo.getUserCredentials(filter = {"userEmail": data.userEmail})
            if user is None:
                raise AppError('username or password is incorrect.',
                           authResponses.signIn.ERROR_INCORRECT_PASSWORD, 400)
            if user['signUpChoice'] == authChoice.GOOGLE:
                raise AppError("User cannot login via manual sign in, as their first sign up was done via Google OAuth method.",
                               authResponses.signIn.ERROR_INVALID_LOGIN_METHOD, 400)
            
            user['userID'] = str(user.pop('_id'))
            cred = normalUser( **user )
        except ValidationError:
            raise AppError("Internal server error",
                           authResponses.signIn.ERROR_INVALID_GETCREDENTIALS_DATA, 500)
        
        if cred.activatedTime is None:
            raise AppError('This user has not activated their account yet.',
                           authResponses.signIn.ERROR_UNACTIVATED_ACCOUNT, 400)
        
        # Check password
        try:
            self.passwordHasher.verify(cred.hashedPassword, data.password)
        except exceptions.VerifyMismatchError:
            raise AppError('username or password is incorrect.',
                           authResponses.signIn.ERROR_INCORRECT_PASSWORD, 400)
        
        user = {
            'lastLoginTime': datetime.now(timezone.utc)
        }
        # Need to add a new password hash to credentials patching if it needs rehash
        if self.passwordHasher.check_needs_rehash(cred.hashedPassword):
            newHash = self.passwordHasher.hash(data.password)
            user['hashedPassword'] = newHash

        id = convertStrToObjectID(field=cred.userID, fieldName='userID', originFuncName='authUsecase.signIn')
        try:
            result = self.userRepo.patchUserCredentials(
                user = user,
                filter = {'_id': id},
            )
            result['userID'] = str(result.pop('_id'))
            result = normalUser( **result )
        except ValidationError:
            raise AppError("Internal server error",
                           authResponses.signIn.ERROR_INVALID_PATCH_FROM_DB, 500)
        
        session.clear() # Clear pre-login session
        session.update( sessionPostLogin( **{
            "userID": cred.userID,
            "CSRFToken": secrets.token_urlsafe(128),
            "needTransactionsReFetch": True # Allow fetching transaction data upon login
        } ).model_dump(exclude_none=True) )
        current_app.session_interface.regenerate(session) # regenerate session ID

        return result
        
    def signUp(self, data: manualSignUpRequest) -> None:
        # If account with this email already exists, don't proceed
        exists = self.userRepo.getUserCredentials(
            filter = {"userEmail": data.userEmail},
            projection = {'_id': True}
        )
        if exists is not None:
            raise AppError('User with this email already exists.',
                           authResponses.signUp.ERROR_EMAIL_ALREADY_EXISTS, 400)
        
        token = secrets.token_urlsafe(128)
        
        # Send account activation email that contains the activation token to client
        subject = "Activate new account for First balance"
        body = f"""\
        <html>
            <head></head>
                <body>
                    <p>Thank you for signing up to First balance.</p>
                    <p>To be able to log in and fully use your account with this email, please click the account activation link below.</p>
                    <p><a href="{self.config.FRONT_END_URL}/activateAccount?token={token}">{self.config.FRONT_END_URL}/activateAccount?token={token}</a></p>
                    
                    <p>If you cannot directly click the link, you can copy and paste it onto your browser's search bar as well.</p>
                    <p>For security purposes, <b>the activation link will expire in 6 hours.</b> 
                    <br></br>Your account will be deleted after that, but you may use the same email to sign up again.</p>
                </body>
        </html>"""
        sender = "firstbalanceproject@gmail.com"
        recipient = data.userEmail

        sendEmail(subject=subject, body=body, sender=sender, recipients=recipient, requiresHTML=True)
        
        # Hash the password and store in DB
        hashcode = self.passwordHasher.hash(data.password)
        result = self.userRepo.patchUserCredentials(
            user = {
                'userEmail': data.userEmail,
                'userName': data.userName,
                'hashedPassword': hashcode,
                'signUpChoice': authChoice.MANUAL,
                'createdTime': datetime.now(timezone.utc),
                'activationToken': token
            },
            filter = {'userEmail': data.userEmail},
        )
        result['userID'] = str(result.pop('_id'))

        # Check result returned by DB to be sure.
        try:
            normalUser( **result )
        except ValidationError as e:
            raise AppError("Internal server error",
                           authResponses.signUp.ERROR_INVALID_PATCH_FROM_DB, 500)
        
    def activateAccount(self, token: str) -> normalUser:
        exists = self.userRepo.getUserCredentials(
            filter={'activationToken': token}, projection={'_id': True, 'activatedTime': True, 'userEmail': True}
        )
        if exists is None or ('activatedTime' in exists.keys() and exists['activatedTime'] is not None):
            raise AppError("User with this email doesn't exists, or has already activated their account.",
                           authResponses.activateAccount.ERROR_EMAIL_DOESNT_EXISTS_OR_ACTIVATED, 400)
        
        id = convertStrToObjectID(field=exists["_id"], fieldName='userID', originFuncName='authUsecase.activateAccount')
        # delete "createdTime" field off the user credentials document to remove the TTL effect
        # And delete "activationToken" too, since it has no more use
        self.userRepo.deleteUserCredentials(fieldsToDelete=['createdTime', 'activationToken'], filter={'_id': id})
        
        try:
            result = self.userRepo.patchUserCredentials(
                user = {'activatedTime': datetime.now(timezone.utc)},
                filter = {'_id': id}, 
            )
            result['userID'] = str(result.pop('_id'))
            result = normalUser( **result )
            return result
        except ValidationError:
            raise AppError("Internal server error",
                           authResponses.activateAccount.ERROR_INVALID_PATCH_FROM_DB, 500)
        
    def requestForgotPassword(self, data: forgotPasswordRequest) -> str:
        """
            Returns the token for password reset.
        """
        # Check if user with this email actually exists
        exists = self.userRepo.getUserCredentials(
            filter={'userEmail': data.userEmail}, projection={'_id': True}
        )
        if not exists:
            raise AppError("User with this email doesn't exists.",
                           authResponses.requestForgotPassword.ERROR_EMAIL_DOESNT_EXISTS, 400)
        
        token = secrets.token_urlsafe(128)

        # Send email to client to reset password
        subject = "Reset your First balance account password"
        body = f"""\
        <html>
            <head></head>
                <body>
                    <p>Please click the link below to reset your password.</p>
                    <p><a href="{self.config.FRONT_END_URL}/resetPassword?token={token}">{self.config.FRONT_END_URL}/resetPassword?token={token}</a></p>
                    
                    <p>If you cannot directly click the link, you can copy and paste it onto your browser's search bar as well.</p>
                    <p>For security purposes, <b>the link will expire in 6 hours.</b> 
                    <br></br>You may request for password reset email again after that.</p>
                </body>
        </html>"""
        sender = "firstbalanceproject@gmail.com"
        recipient = data.userEmail

        sendEmail(subject=subject, sender=sender, recipients=recipient, body=body, requiresHTML=True)

        # Put the token in DB
        try:
            result = self.userRepo.patchUserCredentials(
                user = {'resetPasswordToken': token, 'resetPasswordExpireTime': datetime.now(timezone.utc) + timedelta(hours=6)},
                filter = {'userEmail': data.userEmail},
            )
            result['userID'] = str(result.pop('_id'))
            result = normalUser( **result )
        except ValidationError:
            raise AppError("Internal server error",
                           authResponses.requestForgotPassword.ERROR_INVALID_PATCH_FROM_DB, 500)

        return token
    
    def resetPassword(self, data: resetPasswordRequest, token: str) -> normalUser:
        exists = self.userRepo.getUserCredentials(
            filter={'resetPasswordToken': token},
            projection={'_id': True, 'resetPasswordExpireTime': True}
        )

        if not exists:
            raise AppError("Token invalid, or user doesn't exists, or hasn't requested for password reset token yet.",
                           authResponses.resetPassword.ERROR_INVALID_TOKEN_OR_EMAIL_DOESNT_EXISTS, 400)
        
        present = datetime.now(timezone.utc)
        if exists['resetPasswordExpireTime'] < present:
            raise AppError("The window to reset password has expired.",
                           authResponses.resetPassword.ERROR_RESET_WINDOW_EXPIRED, 400)
        
        hashcode = self.passwordHasher.hash(data.newPassword)
        self.userRepo.deleteUserCredentials(
            filter={'_id': exists['_id']},
            fieldsToDelete=['resetPasswordExpireTime', 'resetPasswordToken'],
        )
        result = self.userRepo.patchUserCredentials(
            user = {'hashedPassword': hashcode},
            filter = {'_id': exists['_id']},
        )
        result['userID'] = str(result.pop('_id'))

        try:
            result = normalUser( **result )
            return result
        except ValidationError:
            raise AppError("Internal server error",
                           authResponses.resetPassword.ERROR_INVALID_PATCH_FROM_DB, 500)

        
    def logout(self) -> None:
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('User is not authenticated.',
                           authResponses.logout.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        session.clear() # clear current session
        session.update( sessionPreLogin(
            CSRFToken = secrets.token_urlsafe(128)
        ).model_dump(exclude_none=True) )
        current_app.session_interface.regenerate(session) # regenerate session ID

    def deleteAccount(self, userID: str) -> None:
        sessionType = checkSessionType(dict(session))
        if sessionType != "postLogin":
            raise AppError('User is not authenticated.',
                           authResponses.deleteAccount.ERROR_UNAUTHENTICATED_SESSION, 401)
        
        id = convertStrToObjectID(field=userID, fieldName='userID', originFuncName='authUsecase.deleteAccount')

        self.userRepo.deleteUserCredentials(filter={'_id': id})
        self.transactionRepo.deleteAll(userID = session['userID'])
        return
