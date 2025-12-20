import traceback
from datetime import datetime, timezone

from argon2 import PasswordHasher
from config.flaskConfig import *
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_session import Session
from pymongo import MongoClient
from redis import Redis
from src.controllers.authController import authController
from src.controllers.transactionController import transactionController
from src.middleware import authMiddleware
from src.repositories.transactionRepo import transactionRepository
from src.repositories.userRepo import userRepository
from src.types.enums.responseCodes.setup import appSetupResponses
from src.usecases.authUsecase import authUsecase
from src.usecases.transactionUsecase import transactionUsecase


def createApp(config: DevConfig | ProdConfig) -> Flask:
    """
        Please supply config with any classes from `config/flaskConfig.py`, except `BaseConfig`.
    """
    try:
        load_dotenv()
        app = Flask(__name__)
        app.config.from_object(config)
        return app
        
    except Exception as e:
        print("Error while setting up server configs: ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": f"Internal server error on initiating server config: {e}",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


def initInfra(config: DevConfig | ProdConfig) -> tuple[Redis, MongoClient]:
    """
        Set up MongoDB and Redis for `Session`. 

        Please supply config with any classes from `config/flaskConfig.py`, except `BaseConfig`.
    """
    try:
        if not config.SESSION_REDIS_URL:
            raise ValueError("SESSION_REDIS_URL must be configured.")
        sessionRedis = Redis.from_url(config.SESSION_REDIS_URL)

        if not config.MONGO_CONFIGS:
            raise ValueError("MONGO_CONFIGS must be configured.")
        mongoClient = MongoClient( **config.MONGO_CONFIGS )

    except Exception:
        print("Error while setting up MongoDB and Redis for Session: ")
        traceback.print_exc()
        print(f"Message code: {appSetupResponses.INTERNAL_SERVER_ERROR}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    return sessionRedis, mongoClient


def initAppAddOns(app: Flask, config: DevConfig | ProdConfig) -> tuple[PasswordHasher, Limiter]:
    """
        Add Session, CORS, Argon2 PasswordHasher, and API limiter. Return `passwordHasher` and `Limiter`.

        Please supply config with any classes from `config/flaskConfig.py`, except `BaseConfig`.
    """
    try:
        Session(app)
        if hasattr(config, 'CORS_CONFIGS'):
            CORS(app, **config.CORS_CONFIGS)
        else:
            CORS(app)

        if hasattr(config, 'ARGON2_PARAMS'):
            passwordHasher = PasswordHasher( **config.ARGON2_PARAMS )
        else:
            passwordHasher = PasswordHasher()

        limiter = Limiter( app=app, **config.LIMITER_CONFIGS )

        return passwordHasher, limiter
    
    except Exception as e:
        print("Error while setting up app Session and CORS: ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": f"Internal server error on setting up app Session and CORS: {e}",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


def initMiddlewares(app: Flask) -> None:
    try:
        app.before_request(authMiddleware.authMiddleware)
    except Exception as e:
        print("Error while setting up auth middleware: ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": f"Internal server error on setting up auth middleware: {e}",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500


def initViews(app: Flask, sessionRedis: Redis, mongoClient: MongoClient, 
              passwordHasher: PasswordHasher, limiter: Limiter, 
              conf: DevConfig | ProdConfig) -> None:
    try:
        userRepo = userRepository(mongo=mongoClient, redisSession=sessionRedis)
        transacRepo = transactionRepository(mongo=mongoClient)

        authUsecases = authUsecase(userRepo=userRepo, transactionRepo= transacRepo, flaskApp=app, 
                                   redisSession=sessionRedis, pwHasher=passwordHasher, conf=conf)
        transacUsecases = transactionUsecase(transactionRepo=transacRepo)
        
        URL_PREFIX: str = '/api'
        authController.register(app, init_argument={"useCase": authUsecases, "limiter": limiter}, route_base='/auth', route_prefix=URL_PREFIX)
        transactionController.register(app, init_argument=transacUsecases, route_base='/transaction', route_prefix=URL_PREFIX)

    except Exception as e:
        print("Error while setting up Flask views (API routes): ")
        traceback.print_exc()
        with app.app_context():
            return jsonify({
                "success": False,
                "message": f"Internal server error on setting up Flask views (API routes) {e}",
                "messageCode": appSetupResponses.INTERNAL_SERVER_ERROR,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500