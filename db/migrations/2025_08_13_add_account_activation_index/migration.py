from config.flaskConfig import DevConfig
from pymongo import MongoClient
from src.types.enums.authChoice import authChoice

client = MongoClient( **DevConfig.MONGO_CONFIGS )
db = client['userCredsDB']
col = db['credsCollection']

# I forgot to add signUpChoice in manual sign up
col.update_many(
    filter = {
        'signUpChoice': {'$exists': False},
        'accessToken': {'$exists': False}
    },
    update = {
        '$set': {
            'signUpChoice': authChoice.MANUAL
        }
    }
)

# Add createdTime index with 6 hours TTL
# sparse = any documents without this field i.e., documents for activated accounts
# will not have TTL, AKA permanent lifetime
col.create_index(
    {'createdTime': 1}, expireAfterSeconds=60 * 60 * 6, sparse=True
)
