import math
import os
from datetime import datetime, timedelta
from secrets import token_hex

import argon2
import google_auth_oauthlib.flow
import requests
from cachelib.file import FileSystemCache
from flask import Flask, jsonify, redirect, request, session, url_for
from flask_caching import Cache
from flask_cors import CORS, cross_origin
from flask_session import Session
from pymongo import MongoClient

# Don't hard code secrets, use os environment variables instead
CLIENT_SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE', 'no file')
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/cloud-platform.read-only']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'

app = Flask(__name__)
# Need a secret key in order to use a Flask session securely
# This has nothing to do with Google OAuth
app.secret_key = token_hex()

# https://flask-caching.readthedocs.io/en/latest/index.html
cacheConfig = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}
app.config.from_mapping(cacheConfig)
cache = Cache(app)
app.config['SESSION_TYPE'] = "cachelib"

# https://flask-session.readthedocs.io/en/latest/config.html#cachelib
app.config['SESSION_CACHELIB'] = FileSystemCache(cache_dir='flask_session', threshold=500)
Session(app)

# https://flask-session.readthedocs.io/en/latest/config.html#relevant-flask-configuration-values
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_NAME='fb_session',
    SESSION_COOKIE_SECURE=False # Must be False when running on HTTP
)

CORS(app, 
     origins=[
         "http://localhost:8081",
         "http://localhost:19000",  # Expo web
         "http://192.168.1.139:*",
         "http://192.168.212.237:*"
     ],
     supports_credentials=True,
     expose_headers=["Set-Cookie"])

DB_USER = os.environ.get('DB_USER', 'no user')
DB_PW = os.environ.get('DB_PW', 'no password')
client = MongoClient(f"mongodb+srv://{DB_USER}:{DB_PW}@cluster0.cbndyae.mongodb.net/")
credDB = client['userCredsDB']
credCollection = credDB['credCollection']
userDataDB = client['userDataDB']

# Using the default parameters. Just hard-coding them so they don't cause error when argon2-cffi updates the default parameters and I don't notice
passwordHasher = argon2.PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=argon2.Type.ID)
ARGON2_PARAMS = "$argon2id$v=19$m=65536,t=3,p=4$"


# Let the Google OAuth library in the front-end handle login on client side and generating state and code
# After login succeed, come to back-end (server side) to exchange code with tokens and other credentials, which can be used to get user info and other things
# https://developers.google.com/identity/protocols/oauth2/web-server#exchange-authorization-code
@app.route('/auth/google_login', methods=['POST'])
@cross_origin(supports_credentials=True)
def googleOAuthCallback():
   data = request.get_json()
   respCode = data.get('code')
   respState = data.get('state')

   # state = session['state']
   # ^ don't use this. State is handled and provided by @react-oauth/google library in front-end already
   # , plus, using session['state'] without ever setting it creates security vulnerabilities

   # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
   flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE,
      scopes=SCOPES,
      state=respState
   )
   
   # flow.redirect_uri = url_for('oauth2callback', _external=True)
   # ^ This one doesn't work.
   flow.redirect_uri = 'postmessage'

   # exchange code with token
   flow.fetch_token(code=respCode)

   # Store credentials in the session.
   # ACTION ITEM: In a production app, you likely want to save these
   #              credentials in a persistent database instead.
   credentials = flow.credentials
   session['credentials'] = {
      'token': credentials.token,
      'refresh_token': credentials.refresh_token,
      'token_uri': credentials.token_uri,
      'client_id': credentials.client_id,
      'client_secret': credentials.client_secret,
      'granted_scopes': credentials.granted_scopes
   }

   # get user data
   # Mostly from this https://stackoverflow.com/a/7138474, adapted from curl to Python requests
   # and https://stackoverflow.com/a/5518085
   try:
      user_data = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo", 
            params={'fields': 'id,email,name,picture'},
            headers={'Authorization': f'Bearer {credentials.token}'},
            timeout=10
         ).json()
   except requests.exceptions.Timeout:
      return jsonify({"error": "Request for user's info timed out"}), 408

   # Save session explicitly to retain user_email until logout
   session.modified = True
   session.permanent = True
   
   cred = {
      "UserEmail": user_data['email'],
      "UserName": user_data['name'],
      "UserID": user_data['id'],
      "UserPicture": user_data['picture'],
      "Token": credentials.token,
      "RefreshToken": credentials.refresh_token,
      "TokenURI": credentials.token_uri,
      "ClientID": credentials.client_id,
      "GrantedScopes": credentials.granted_scopes
   }

   # If user has never logged in before, put their credentials into credential database
   findOneRes = credCollection.find_one({"UserEmail": user_data['email']})
   if findOneRes is None:
      result = credCollection.insert_one(cred)
   else:
      # If found a collection, update fields regarding Google's OAuth (if they are already presented, meaning this user has logged in with Google before), 
      # or insert them (if they don't exist yet, meaning this is the first time this user login by Google)
      result = credCollection.update_one(
         {
            "UserEmail": findOneRes['UserEmail']
         },
         { '$set': {
            "UserName": user_data['name'],
            "UserID": user_data['id'],
            "UserPicture": user_data['picture'],
            "Token": credentials.token,
            "RefreshToken": credentials.refresh_token,
            "TokenURI": credentials.token_uri,
            "ClientID": credentials.client_id,
            "GrantedScopes": credentials.granted_scopes
         }}
      )

   user_data_collection = userDataDB[user_data['email']]
   if not user_data_collection.find_one():
      # Initialize if this is first time of user
      # (we just need to input a document when creating a DB/collection. MongoDB doesn't allow creating an empty collection)
      # Don't forget to do this when user login for first time ever by manual sign-up as well
      user_data_collection.insert_one({"Initialized": True})

   # Store as least additional data into cookie as possible
   session['user_email'] = user_data['email']
   session['user_id'] = user_data['id']

   return jsonify(cred), 200


@app.route('/debug/session')
@cross_origin(supports_credentials=True)
def debug_session():
   return jsonify(dict(session)), 200

@app.route('/debug/cookies')
@cross_origin(supports_credentials=True)
def debug_cookies():
   return jsonify(request.cookies), 200



@app.route('/auth/signIn', methods=['POST'])
@cross_origin(supports_credentials=True)
def signIn():
   data = request.get_json()
   email = data.get('Email')
   password = data.get('Password')

   # TODO: check input for NoSQL injection

   exists = credCollection.find_one({"UserEmail": email})
   if not exists:
      return jsonify({"error": "This user doesn't exist. Please sign up first to create a password, or login by Google."}), 404
   
   # Check password
   try:
      salt = exists['Salt']
      hashedPW = exists['HashedPassword']
      verify = passwordHasher.verify(ARGON2_PARAMS + "$".join([salt, hashedPW]), password)
      if verify:
         session['user_email'] = email
         cred = {
            "UserEmail": email,
            "UserName": exists['UserName']
         }
         return jsonify(cred), 200
      
   except argon2.exceptions.VerifyMismatchError:
      return jsonify({"error": "Username or password is incorrect"}), 401
   except Exception as e:
      return jsonify({'error': e}), 500
   

@app.route('/auth/signUp', methods=['POST'])
@cross_origin(supports_credentials=True)
def signUp():
   data = request.get_json()
   email = data.get('Email')
   name = data.get('Name')
   password = data.get('Password')

   exists = credCollection.find_one({"UserEmail": email})
   if exists:
      return jsonify({"error": "User with this email already exists."}), 409
   
   # TODO: check input for NoSQL injection

   try:
      # Stuffs in the string returned from passwordHasher.hash(): https://stackoverflow.com/a/58431975
      result = passwordHasher.hash(password)
      salt, hashedPw = result[31:].split("$")
      
      cred = {
         "UserEmail": email,
         "UserName": name,
         "Salt": salt,
         "HashedPassword": hashedPw
      }
      insertResult = credCollection.insert_one(cred)
      return jsonify({"message": "User added successfully"}), 201
   except Exception as e:
      return jsonify({"error": e}), 500
   

# https://stackoverflow.com/q/3521290
@app.route('/logout', methods=['POST'])
@cross_origin(supports_credentials=True)
def logout():
   # Just in rare case the user info/logout page is somehow accessible without logging in first
   # By ProtectedRoute in front-end, this shouldn't happen, but who knows
   if 'user_email' not in session:
      redirect('/')
      return jsonify({"error": "User not authenticated"}), 401
   
   # remove user details from session
   [session.pop(key) for key in list(session.keys())]
   return "Logged out successfully", 200


# re-fetch records every time a page come into focus (useFocusEffect in front-end) by loading them from the database
@app.route('/get_all_records', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def get_records():
    print(session)
   #  data = request.get_json()
   #  email = data.get("Email")
   #  print(email)

    if 'user_email' not in session:
       return jsonify({"error": "User not authenticated"}), 401
    
    try:
      # If inside collection of the user only has the {'Initialized': true} document, then this user has no actual data yet
      # DON'T include the {'Initialized': true} document in records. It's not actual user data and front-end logic only handles documents with RecordItem interface.
      # Put simply, get all documents (which have no 'Initialized' field) except the {'Initialized': true} one.
      records = list(userDataDB[session['user_email']].find({'Initialized': {'$exists': False}}))
      # records = list(userDataDB[email].find({'Initialized': {'$exists': False}}))
      for record in records:
         record["_id"] = str(record["_id"])
    except Exception as e:
       print(e)
       return jsonify({"error": str(e)}), 500
       
    return jsonify({"all_records": records}), 200


@app.route('/add_record', methods=['POST'])
@cross_origin(supports_credentials=True)
def add_record():
    data = request.get_json()

    TransactionName = data.get("TransactionName")
    AccountID = data.get("AccountID")
    Value = data.get("Value")
    Date = data.get("Date")
    Memo = data.get("Memo")

    # transaction name, account ID, Value, and Date are required
    if not TransactionName or not AccountID or not Value or not Date:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
      Date_obj = datetime.strptime(Date, "%d-%m-%Y")
    except ValueError:
      return jsonify({"error": "Invalid Date format. Expect DD-MM-YYYY"}), 400
    
    # Check whether record with the same data (all required fields are the same) already exist
    existing = userDataDB[session['user_email']].find_one({
      "TransactionName": TransactionName,
      "AccountID": AccountID,
      "Value": Value,
      "Date": Date
    })
    if existing:
      return jsonify({"error": "Record already exists"}), 400
    
    new_record = {
       "TransactionName": TransactionName,
       "AccountID": AccountID,
       "Value": Value,
       "Date": Date, # No point to keep date as datetime object, "DD-MM-YYYY" is enough
       "Memo": Memo
    }

    result = userDataDB[session['user_email']].insert_one(new_record)
    return jsonify({"message": "Record added successfully"}), 201


@app.route('/delete_one', methods=['DELETE'])
@cross_origin(supports_credentials=True)
def delete_one():
   data = request.get_json()
   TransactionName = data.get("TransactionName")
   AccountID = data.get("AccountID")
   Value = data.get("Value")
   Date = data.get("Date")
   Memo = data.get("Memo")

   result = userDataDB[session['user_email']].delete_one({
      "TransactionName": TransactionName,
      "AccountID": AccountID,
      "Value": Value,
      "Date": Date,
      "Memo": Memo
   })

   return jsonify({"message": "Successfully deleted a transaction"}), 200


@app.route('/delete_many', methods=['DELETE'])
@cross_origin(supports_credentials=True)
def delete_many():
   try:
      data = request.get_json()
      TNameFilter = data.get("TransactionName")
      AccountIDFilter = data.get("AccountID")
      minValueFilter = data.get("MinValue")
      maxValueFilter = data.get("MaxValue")
      startDateFilter = data.get("StartDate")
      endDateFilter = data.get("EndDate")
      MemoFilter = data.get("Memo")

      # For string fields, if user gave "" as filter, then
      # match documents with any value for those fields for deletion

      # For any type of fields, if want to match any values,
      # use { "$exists": True }, not {}. If we use {}, MongoDB will only
      # match documents where that field is an empty object.

      valueQuery = {}
      if minValueFilter is None or math.isnan(minValueFilter):
         valueQuery = { "$lte": maxValueFilter }
      elif maxValueFilter is None or math.isnan(maxValueFilter):
         valueQuery = { "$gte": minValueFilter }
      else: # both not None
         valueQuery = { "$gte": minValueFilter, "$lte": maxValueFilter }
      if minValueFilter is None or math.isnan(minValueFilter) \
         and maxValueFilter is None or math.isnan(maxValueFilter):
         valueQuery = { "$exists": True }

      # date handling
      def _to_ISO_format(date_str):
         # expect "DD-MM-YYYY" input
         try:
            return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
         except ValueError:
            return date_str  # Fallback if already formatted
      
      def _to_DD_MM_YYYY(date_str):
         try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
         except ValueError:
            return date_str
      
      # change documents dates to "YYYY-MM-DD"
      for rec in userDataDB[session['user_email']].find({}):
         rec["Date"] = _to_ISO_format(rec["Date"])
         userDataDB[session['user_email']].update_one({"_id": rec["_id"]}, {"$set": {"Date": rec["Date"]}})

      # And change the filter too
      dateQuery = {}
      if startDateFilter is not None:
         dateQuery["$gte"] = _to_ISO_format(startDateFilter)
      if endDateFilter is not None:
         dateQuery["$lte"] = _to_ISO_format(endDateFilter)
      if len(dateQuery) == 0: # both None
         dateQuery = { "$exists": True }


      query = {
         "TransactionName": {"$regex": TNameFilter, "$options": "i"},
         "AccountID": {"$regex": AccountIDFilter, "$options": "i"},
         "Value": valueQuery,
         "Date": dateQuery,
         "Memo": {"$regex": MemoFilter, "$options": "i"}
      }
      result = userDataDB[session['user_email']].delete_many(query)

      # Finally, convert date of remaining documents back to "DD-MM-YYYY"
      all_remaining = userDataDB[session['user_email']].find({})
      for rec in all_remaining:
         rec["Date"] = _to_DD_MM_YYYY(rec["Date"])
         userDataDB[session['user_email']].update_one({"_id": rec["_id"]}, {"$set": {"Date": rec["Date"]}})
   
   except Exception as e:
      app.logger.error(f"Delete many failed: {str(e)}")
      return jsonify({"error": str(e)}), 500

   return jsonify({"message": f"Successfully deleted {result.deleted_count} matched transactions"}), 200


@app.route('/update_one', methods=['PATCH'])
@cross_origin(supports_credentials=True)
def update_one():
   data = request.get_json()

   # Format of incoming data:
   # {
   #    "original": {"TransactionName": ..., "AccountID"...},
   #    "newData": {"TransactionName": ..., "AccountID"...}
   # }
   original = data.get("original", {})
   new = data.get("newData", {})

   originalTransactionName = original.get("TransactionName")
   originalAccountID = original.get("AccountID")
   originalValue = original.get("Value")
   originalDate = original.get("Date")
   originalMemo = original.get("Memo")

   newTransactionName = new.get("TransactionName")
   newAccountID = new.get("AccountID")
   newValue = new.get("Value")
   newDate = new.get("Date")
   newMemo = new.get("Memo")

   checkDup = userDataDB[session['user_email']].find_one({
      "TransactionName": newTransactionName,
      "AccountID": newAccountID,
      "Value": newValue,
      "Date": newDate,
      "Memo": newMemo
   })
   if checkDup:
      return jsonify({"error": "A record with the exact same data already exists"}), 400

   result = userDataDB[session['user_email']].update_one(
      {
         "TransactionName": originalTransactionName,
         "AccountID": originalAccountID,
         "Value": originalValue,
         "Date": originalDate,
         "Memo": originalMemo
      },
      { "$set": {
         "TransactionName": newTransactionName,
         "AccountID": newAccountID,
         "Value": newValue,
         "Date": newDate,
         "Memo": newMemo
      }}
   )

   return jsonify({"message": "Successfully updated a transaction"}), 200



if __name__ == '__main__':
   # When running locally, disable OAuthlib's HTTPs verification.
   # ACTION ITEM for developers:
   #     When running in production *do not* leave this option enabled.
   os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

   # This disables the requested scopes and granted scopes check.
   # If users only grant partial request, the warning would not be thrown.
   os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

   app.run(port=5000)