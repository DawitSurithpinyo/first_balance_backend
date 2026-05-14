from flask import Flask, g, request
from flask_request_id import RequestID

def registerRequestIDMiddleware(app: Flask):
    """
        Register RequestID middleware
    """
    RequestID(app)

def addRequestIDCtx():
    """
        Add request ID to request's context
    """
    g.request_id = request.environ.get("FLASK_REQUEST_ID")