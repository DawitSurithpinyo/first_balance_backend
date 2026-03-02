import os

from dotenv import load_dotenv

load_dotenv()
DEV_CLIENT_SECRETS_FILE = os.getenv('DEV_CLIENT_SECRETS_FILE', 'no file')
SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 
          'https://www.googleapis.com/auth/userinfo.profile',
          'openid']