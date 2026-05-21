import os

from dotenv import load_dotenv

load_dotenv()
DEV_CLIENT_SECRETS_FILE = os.getenv('DEV_CLIENT_SECRETS_FILE')
DEV_CLIENT_ID = os.getenv('DEV_CLIENT_ID')
SCOPES = ['https://www.googleapis.com/auth/userinfo.profile', 
          'https://www.googleapis.com/auth/userinfo.email',
        'openid']