import os

from dotenv import load_dotenv
from flask_limiter.util import get_remote_address

load_dotenv()
class BaseConfig(object):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
        

class DevConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.getenv("DEV_FLASK_SECRET_KEY", "no flask secret key")

    # CACHE_TYPE = "RedisCache"
    # CACHE_REDIS_URL = os.getenv('DEV_CACHE_REDIS_URL', 'no cache Redis url')

    SESSION_TYPE = "redis"
    SESSION_COOKIE_NAME = "First_balance"
    SESSION_COOKIE_SECURE = False


    # Below are other custom configs that are not for the Flask app
    PORT = 5000 # for app.run()
    CORS_CONFIGS = {
        "origins": ['http://localhost:5173', 'http://localhost:5000'],
        "supports_credentials": True,
        "expose_headers": ["X-CSRF-Token"], # custom headers must be exposed so that front-end can receive them
        "allow_headers": ["X-CSRF-Token"]
    } # For CORS()

    MONGO_CONFIGS = {
        "host": os.getenv('DEV_DATABASE_URL', 'no MongoDB url'),
        "tz_aware": True
    }
    SESSION_REDIS_URL = os.getenv('DEV_SESSION_REDIS_URL', 'no session Redis url')

    LIMITER_CONFIGS = {
        "key_func": get_remote_address,
        "default_limits": ['4 per second'], # individually apply to all routes
        "application_limits": ['500 per day'], # shared limit across all routes
        "meta_limits": ['5 per day'], # how many times client can hit any defined limits
        "headers_enabled": True,
        "storage_uri": os.getenv('DEV_LIMITER_REDIS_URL'),
        # "storage_options": {
        #     "tz_aware": True
        # }
    }