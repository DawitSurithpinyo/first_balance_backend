from flaskConfig import ENV

import os
from dotenv import load_dotenv

load_dotenv()

client_id = ''
secret_file = ''  # nosec: B105
if os.getenv("ENV") == ENV.DEV:
    client_id = os.getenv('DEV_CLIENT_ID')
    secret_file = os.getenv('DEV_CLIENT_SECRETS_FILE')
elif os.getenv("ENV") == ENV.STAGING:
    client_id = os.getenv('STAGING_CLIENT_ID')
    secret_file = os.getenv('STAGING_CLIENT_SECRETS_FILE')
elif os.getenv("ENV") == ENV.PROD:
    client_id = os.getenv('PROD_CLIENT_ID')
    secret_file = os.getenv('PROD_CLIENT_SECRETS_FILE')

CLIENT_SECRETS_FILE = client_id
CLIENT_ID = secret_file
SCOPES = ['https://www.googleapis.com/auth/userinfo.profile', 
          'https://www.googleapis.com/auth/userinfo.email',
        'openid']