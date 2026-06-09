from src.types.error.AppError import AppError
from flask import jsonify
import traceback
from datetime import datetime, timezone

def sendError(e: Exception):
    if isinstance(e, AppError):
        if e.statusCode == 500:
            traceback.print_exc()
        return jsonify({
            "success": False,
            "message": e.message,
            "messageCode": e.messageCode,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), e.statusCode
    
    # Unhandled error, something very wrong and unexpected
    traceback.print_exc()
    return jsonify({
        "success": False,
        "message": "Internal server error",
        "messageCode": "INTERNAL_SERVER_ERROR",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 500