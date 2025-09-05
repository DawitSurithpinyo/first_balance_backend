import requests
from flask import session

# from src.types.user.GET import getUserGoogleProfileResponse


def getUserGoogleProfile(token: str):
    # get user data after completing the Google OAuth v2 flow
    # Mostly from this https://stackoverflow.com/a/7138474, adapted from curl to Python requests
    # and https://stackoverflow.com/a/5518085
    request_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo", 
        params={'fields': 'email,name,picture'},
        headers={'Authorization': f'Bearer {token}'},
        timeout=10
    ).json()

    # Rename the key 'picture' to 'pictureLink'
    # Because it's a link to the picture, not the picture itself
    request_res['pictureLink'] = request_res.pop('picture')

    # user_data = getUserGoogleProfileResponse( **request_res )
    # return user_data
    return request_res