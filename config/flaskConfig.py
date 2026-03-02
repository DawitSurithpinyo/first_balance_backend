import os

from flask_limiter.util import get_remote_address

class ENV(object):
    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"

class BaseConfig(object):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
        

class DevConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.getenv("DEV_FLASK_SECRET_KEY")

    # CACHE_TYPE = "RedisCache"
    # CACHE_REDIS_URL = os.getenv('DEV_CACHE_REDIS_URL', 'no cache Redis url')

    SESSION_TYPE = "redis"
    SESSION_COOKIE_NAME = "First_balance"
    SESSION_COOKIE_SECURE = False


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

    LIMITER_CONFIGS = {
        "key_func": get_remote_address,
        "default_limits": ['4 per second'], # individually apply to all routes
        "application_limits": ['500 per day'], # shared limit across all routes
        "meta_limits": ['5 per day'], # how many times client can hit any defined limits
        "headers_enabled": True,
        "storage_uri": f"redis://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/1",
        # "storage_options": {
        #     "tz_aware": True
        # }
    }

class StagingConfig(BaseConfig):
    PORT = 5000
    FRONT_END_URL = 'https://firstbalance.net'

class ProdConfig(BaseConfig):
    PORT = 5000
    FRONT_END_URL = 'https://firstbalance.net'