import traceback
from datetime import datetime, timezone

from argon2 import PasswordHasher
from config.flaskConfig import *
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_session import Session
from pymongo import MongoClient
from redis import Redis
from src.controllers.authController import authController
from src.controllers.transactionController import transactionController
from src.middleware import authMiddleware, requestID
from src.repositories.transactionRepo import transactionRepository
from src.repositories.userRepo import userRepository
from src.types.enums.responseCodes.setup import appSetupResponses
from src.usecases.authUsecase import authUsecase
from src.usecases.transactionUsecase import transactionUsecase

def getConf() -> DevConfig | StagingConfig | ProdConfig:
    """
        Get type of config based on environment variable 'ENV'
    """
    try:
        env = os.getenv("ENV")
        if env is None:
            raise ValueError("Missing env variable 'ENV'")
        if env == ENV.DEV:
            return DevConfig()
        elif env == ENV.STAGING:
            return StagingConfig()
        elif env == ENV.PROD:
            return ProdConfig()
        else:
            raise ValueError(f"Env variable 'ENV' has an unknown value: {env}")

    except Exception as e:
        print(f"Error while trying to get ENV env variable: {e}")
        traceback.print_exc()
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")


def createApp(config: DevConfig | StagingConfig | ProdConfig) -> Flask:
    """
        Please supply config with any classes from `config/flaskConfig.py`, except `BaseConfig`.
    """
    try:
        app = Flask(__name__)
        app.config.from_object(config)
        return app
        
    except Exception:
        print("Error while setting up server configs: ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": "Internal server error",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


def initInfra(config: DevConfig | StagingConfig | ProdConfig) -> tuple[Redis, MongoClient]:
    """
        Set up MongoDB and Redis for `Session`. 

        Please supply config with any classes from `config/flaskConfig.py`, except `BaseConfig`.
    """
    try:
        if hasattr(config, 'SESSION_REDIS_CONFIGS'):
            sessionRedis = Redis( **config.SESSION_REDIS_CONFIGS )
        else:
            raise ValueError("SESSION_REDIS_CONFIGS must be configured.")

        if hasattr(config, 'MONGO_CONFIGS'):
            mongoClient = MongoClient( **config.MONGO_CONFIGS )
        else:
            raise ValueError("MONGO_CONFIGS must be configured.")

    except Exception:
        print("Error while setting up MongoDB and Redis for Session: ")
        traceback.print_exc()
        print(f"Message code: {appSetupResponses.INTERNAL_SERVER_ERROR}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    return sessionRedis, mongoClient


def initAppAddOns(app: Flask, sessionRedis: Redis, config: DevConfig | StagingConfig | ProdConfig) -> tuple[PasswordHasher, Limiter]:
    """
        Add Session, CORS, Argon2 PasswordHasher, and API limiter. Return `passwordHasher` and `Limiter`.
        `sessionRedis` is needed, because Flask-Session requires pointing `app.config['SESSION_REDIS']` to the desired Redis instance.

        Please supply config with any classes from `config/flaskConfig.py`, except `BaseConfig`.
    """
    try:
        # Set app.config['SESSION_REDIS'] before setting Session to make sure Session point to the right Redis instance
        # Have to individually assign config like this because this is how it must be done on Flask-Session :(
        app.config['SESSION_REDIS'] = sessionRedis
        app.config['SESSION_COOKIE_NAME'] = config.SESSION_COOKIE_NAME
        app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE
        app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
        app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE
        app.config['SESSION_COOKIE_PATH'] = config.SESSION_COOKIE_PATH
        app.config['PERMANENT_SESSION_LIFETIME'] = config.SESSION_LIFETIME
        app.config['SESSION_ID_LENGTH'] = config.SESSION_ID_LENGTH

        Session(app)

        if hasattr(config, 'CORS_CONFIGS'):
            CORS(app, **config.CORS_CONFIGS)
        else:
            raise ValueError("Expect CORS configuration")

        if hasattr(config, 'ARGON2_PARAMS'):
            passwordHasher = PasswordHasher( **config.ARGON2_PARAMS )
        else:
            # Argon2-cffi already provides sane default configs, so no custom config is fine
            passwordHasher = PasswordHasher()

        if hasattr(config, 'LIMITER_CONFIGS'):
            limiter = Limiter( app=app, **config.LIMITER_CONFIGS )
        else:
            raise ValueError("Expect Limiter configuration")

        return passwordHasher, limiter
    
    except Exception:
        print("Error while setting up app Session and CORS: ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": "Internal server error",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


def initMiddlewares(app: Flask) -> None:
    """
        Auth and Request ID middleware
    """
    try:
        requestID.registerRequestIDMiddleware(app)

        app.before_request(requestID.addRequestIDCtx)
        app.before_request(authMiddleware.authMiddleware)
    except Exception:
        print("Error while setting up auth middleware: ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": "Internal server error",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


def initViews(app: Flask, mongoClient: MongoClient, 
              passwordHasher: PasswordHasher, limiter: Limiter, 
              conf: DevConfig | StagingConfig | ProdConfig) -> None:
    try:
        userRepo = userRepository(mongo=mongoClient)
        transacRepo = transactionRepository(mongo=mongoClient)

        authUsecases = authUsecase(userRepo=userRepo, transactionRepo=transacRepo, 
                                   pwHasher=passwordHasher, conf=conf)
        transacUsecases = transactionUsecase(transactionRepo=transacRepo)
        
        URL_PREFIX: str = '/api'
        authController.register(app, init_argument={"useCase": authUsecases, "limiter": limiter}, route_base='/auth', route_prefix=URL_PREFIX)
        transactionController.register(app, init_argument={"useCase": transacUsecases, "limiter": limiter}, route_base='/transaction', route_prefix=URL_PREFIX)

    except Exception:
        print("Error while setting up Flask views (API routes): ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": "Internal server error",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500