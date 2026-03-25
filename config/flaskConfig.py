import os

from flask_limiter.util import get_remote_address
from redis.retry import Retry
from redis.exceptions import (TimeoutError, ConnectionError)
from redis.backoff import ExponentialBackoff
from datetime import timedelta

class ENV(object):
    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"

class BaseConfig(object):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_PATH = "/"
        

class DevConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.getenv("DEV_FLASK_SECRET_KEY")

    # CACHE_TYPE = "RedisCache"
    # CACHE_REDIS_URL = os.getenv('DEV_CACHE_REDIS_URL', 'no cache Redis url')

    SESSION_TYPE = "redis"
    SESSION_COOKIE_NAME = "First_balance"
    SESSION_COOKIE_SECURE = False
    SESSION_LIFETIME = timedelta(days=7)
    SESSION_ID_LENGTH = 128


    # Below are other custom configs that are not for the Flask app
    PORT = 5000
    FRONT_END_URL = 'http://localhost:5173'
    CORS_CONFIGS = {
        "origins": [FRONT_END_URL],
        "supports_credentials": True,
        "expose_headers": ["X-CSRF-Token"], # custom headers must be exposed so that front-end can receive them
        "allow_headers": ["X-CSRF-Token"]
    } # For CORS()

    MONGO_CONFIGS = {
        "host": os.getenv('DEV_DATABASE_URL'),
        "tz_aware": True
    }

    REDIS_HOST = os.getenv('DEV_REDIS_HOST')
    REDIS_USER = os.getenv('DEV_REDIS_USER')
    REDIS_PASS = os.getenv('DEV_REDIS_PASS')
    REDIS_PORT = os.getenv('DEV_REDIS_PORT')
    REDIS_HEALTH_CHECK_INTERVAL = 25
    REDIS_RETRY = Retry(ExponentialBackoff(cap=10, base=1), retries=25)
    REDIS_RETRY_ON_ERROR = [ConnectionError, TimeoutError]
    REDIS_SOCKET_KEEPALIVE = True

    SESSION_REDIS_CONFIGS = {
        "host": REDIS_HOST,
        "username": REDIS_USER,
        "password": REDIS_PASS,
        "port": REDIS_PORT,
        "db": 0,
        "health_check_interval": REDIS_HEALTH_CHECK_INTERVAL,
        "retry": REDIS_RETRY,
        "retry_on_error": REDIS_RETRY_ON_ERROR,
        "socket_keepalive": REDIS_SOCKET_KEEPALIVE
    }

    LIMITER_CONFIGS = {
        "key_func": get_remote_address,
        "default_limits": ['4 per second'], # individually apply to all routes
        "application_limits": ['500 per day'], # shared limit across all routes
        "meta_limits": ['5 per day'], # how many times client can hit any defined limits
        "headers_enabled": True,
        "storage_uri": f"redis://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/1",
        "storage_options": {
            "db": 1,
            "health_check_interval": REDIS_HEALTH_CHECK_INTERVAL,
            "retry": REDIS_RETRY,
            "retry_on_error": REDIS_RETRY_ON_ERROR,
            "socket_keepalive": REDIS_SOCKET_KEEPALIVE
        }
    }

class StagingConfig(BaseConfig):
    PORT = 5000
    FRONT_END_URL = 'https://firstbalance.net'

class ProdConfig(BaseConfig):
    PORT = 5000
    FRONT_END_URL = 'https://firstbalance.net'