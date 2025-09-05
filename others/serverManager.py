import os
import sys
from datetime import datetime
from secrets import token_hex

from cachelib import redis
from flask import Flask, jsonify
from flask_caching import Cache
from flask_cors import CORS
from pymongo import MongoClient

from flask_session import Session


class serverManager:
    def __init__(self) -> None:
        self.app = Flask(__name__)
        self.mongo = None
        self.redis = None

    def setupServer(self) -> None:
        """
        setup app secret key -> app caching with Redis -> app session -> CORS -> MongoClient
        """
        try:
            # Flask session secret key
            self.app.secret_key = token_hex()

            # Flask caching and session
            config = {
                "DEBUG": True,          # some Flask specific configs
                "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
                "CACHE_DEFAULT_TIMEOUT": 300
            }
            self.app.config.from_mapping(config)
            Cache(self.app)
            self.app.config['SESSION_TYPE'] = "cachelib"
            self.redis = redis.RedisCache(host=os.getenv('REDIS_HOST', 'no host'), 
                                            port=os.getenv('REDIS_PORT', 'no port'), 
                                            password=os.getenv('REDIS_PASSWORD', 'no password'))
            self.app.config['SESSION_CACHELIB'] = self.redis
            Session(self.app)
            self.app.config.update(
                SESSION_COOKIE_HTTPONLY=True,
                SESSION_COOKIE_SAMESITE='None',
                SESSION_COOKIE_NAME='fb_session',
                SESSION_COOKIE_SECURE=False # Must be False when running on HTTP
            )

            CORS(self.app, origins=['http://localhost:8081', 'http://localhost:5000'], 
                supports_credentials=True, expose_headers=["Set-Cookie"])
            
            self.mongo = MongoClient(os.getenv('DATABASE_URL', 'no mongoDB url'))
            
        except Exception as e:
            print(f"Error while setting up server configs: {e}")
            return jsonify({
                "success": False,
                "error": f"Internal server error on initiating server config: {e}",
                "timestamp": datetime.now().isoformat()
            }), 500
        
    def getApp(self) -> Flask:
        return self.app
    
    def getMongoDB(self) -> MongoClient:
        return self.mongo
    
    def getRedis(self) -> redis.RedisCache:
        return self.redis
    

server = serverManager()