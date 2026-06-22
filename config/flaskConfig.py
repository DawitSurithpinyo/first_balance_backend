import os

from flask_limiter.util import get_remote_address
from redis.retry import Retry
from redis.exceptions import TimeoutError, ConnectionError
from redis.backoff import ExponentialBackoff
from datetime import timedelta

class ENV(object):
    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"

class BaseConfig(object):
    def __init__(self):
        self.DEBUG = False

        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        self.SESSION_COOKIE_PATH = "/"


class DevConfig(BaseConfig):
    def __init__(self):
        super().__init__()

        # Flask configs
        self.DEBUG = True
        self.SECRET_KEY = os.getenv("DEV_FLASK_SECRET_KEY")

        # Session configs
        self.SESSION_TYPE = "redis"
        self.SESSION_COOKIE_NAME = "First_balance"
        self.SESSION_COOKIE_SECURE = False
        self.SESSION_LIFETIME = timedelta(days=7)
        self.SESSION_ID_LENGTH = 128

        # App configs
        self.PORT = 5000
        self.FRONT_END_URL = "http://localhost:5173"
        self.FRONT_END_BUILD_URL = "http://localhost:4173"

        # CORS
        self.CORS_CONFIGS = {
            "origins": [self.FRONT_END_URL, self.FRONT_END_BUILD_URL],
            "supports_credentials": True,
            "expose_headers": ["X-CSRF-Token", "X-Request-ID"],
            "allow_headers": ["X-CSRF-Token", "Origin", "Content-Type", "Accept", "Authorization"],
        }

        # Mongo
        self.MONGO_CONFIGS = {
            "host": os.getenv("DEV_DATABASE_URL"),
            "tz_aware": True,
        }

        # Redis base configs
        self.REDIS_HOST = os.getenv("DEV_REDIS_HOST")
        self.REDIS_USER = os.getenv("DEV_REDIS_USER")
        self.REDIS_PASS = os.getenv("DEV_REDIS_PASS")

        redis_port = os.getenv("DEV_REDIS_PORT")
        self.REDIS_PORT = int(redis_port) if redis_port else None

        self.REDIS_HEALTH_CHECK_INTERVAL = 25
        self.REDIS_RETRY = Retry(ExponentialBackoff(cap=10, base=1), retries=25)
        self.REDIS_RETRY_ON_ERROR = [ConnectionError, TimeoutError]
        self.REDIS_SOCKET_KEEPALIVE = True

        # Flask-Session Redis
        self.SESSION_REDIS_CONFIGS = {
            "host": self.REDIS_HOST,
            "username": self.REDIS_USER,
            "password": self.REDIS_PASS,
            "port": self.REDIS_PORT,
            "db": 0,
            "health_check_interval": self.REDIS_HEALTH_CHECK_INTERVAL,
            "retry": self.REDIS_RETRY,
            "retry_on_error": self.REDIS_RETRY_ON_ERROR,
            "socket_keepalive": self.REDIS_SOCKET_KEEPALIVE,
        }

        # Flask-Limiter
        self.LIMITER_CONFIGS = {
            "key_func": get_remote_address,
            "default_limits": ["10 per second"],
            "application_limits": ["1000 per day"],
            "meta_limits": ["5 per day"],
            "headers_enabled": True,
            "storage_uri": (
                f"redis://{self.REDIS_USER}:{self.REDIS_PASS}"
                f"@{self.REDIS_HOST}:{self.REDIS_PORT}/1"
            ),
            "storage_options": {
                "db": 1,
                "health_check_interval": self.REDIS_HEALTH_CHECK_INTERVAL,
                "retry": self.REDIS_RETRY,
                "retry_on_error": self.REDIS_RETRY_ON_ERROR,
                "socket_keepalive": self.REDIS_SOCKET_KEEPALIVE,
            },
        }

class StagingConfig(BaseConfig):
    def __init__(self):
        super().__init__()

        self.PORT = 5000
        self.FRONT_END_URL = 'https://firstbalance.net'

class ProdConfig(BaseConfig):
    def __init__(self):
        super().__init__()

        self.PORT = 5000
        self.FRONT_END_URL = 'https://firstbalance.net'