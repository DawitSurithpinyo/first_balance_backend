import os
from dotenv import load_dotenv

load_dotenv()

client_id = ''
secret_file = ''  # nosec: B105

env = os.getenv("ENV")
if env == "DEV":
    client_id = os.getenv('DEV_CLIENT_ID')
    secret_file = os.getenv('DEV_CLIENT_SECRETS_FILE')
elif env == "STAGING":
    client_id = os.getenv('STAGING_CLIENT_ID')
    secret_file = os.getenv('STAGING_CLIENT_SECRETS_FILE')
elif env == "PROD":
    client_id = os.getenv('PROD_CLIENT_ID')
    secret_file = os.getenv('PROD_CLIENT_SECRETS_FILE')


CLIENT_SECRETS_FILE = secret_file
CLIENT_ID = client_id
SCOPES = ['https://www.googleapis.com/auth/userinfo.profile', 
          'https://www.googleapis.com/auth/userinfo.email',
        'openid']