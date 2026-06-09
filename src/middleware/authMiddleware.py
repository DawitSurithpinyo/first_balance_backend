from flask import request, session, current_app
from src.types.enums.responseCodes.auth import authResponses
from src.types.error.AppError import AppError
from src.utils.checkSessionType import checkSessionType
from infrastructure.http.response import sendError

# some endpoints are public or handle credential checking on their own
whiteList = ['authController:getCredentials']

def authMiddleware():
    try:
        if request.endpoint is None:
            # if invalid API route, request.endpoint will be null
            raise AppError("API route not found.",
                           authResponses.middleware.ERROR_ROUTE_NOT_FOUND, 404)
        
        if request.endpoint in whiteList:
            # Automatically go to destination route if it's in whiteList
            return
        
        sessionType = checkSessionType(dict(session))
        if sessionType == "unknown":
            # Authenticated users should have server-side session
            # Even when they are not logged in yet, server should've established a pre-login session with login CSRF token already
            raise AppError("User is unauthenticated.",
                           authResponses.middleware.ERROR_INVALID_SESSION, 401)
        
        if request.method not in ['GET', 'HEAD', 'OPTIONS']:
            # Check CSRF token for state-changing requests
            incomingCSRFToken = request.headers.get('X-CSRF-Token', type = str, default = None)
            sessionCSRFToken = session['CSRFToken']
            if incomingCSRFToken is None or sessionCSRFToken is None or incomingCSRFToken != sessionCSRFToken:
                raise AppError("Invalid CSRF token.",
                               authResponses.middleware.ERROR_INVALID_CSRF_TOKEN, 401)
        
    except Exception as e:
        with current_app.app_context():
            return sendError(e)