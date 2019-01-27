import json
import time
import logging
import requests
from webexteamssdk import WebexTeamsAPI

logger = logging.getLogger(__name__) # Creating logger for logging across this module

# Module constants
AUTH_API_URL = 'https://cloudsso.cisco.com/as/token.oauth2'
HELLO_API_URL = 'https://api.cisco.com/hello'
BUG_API_URL = 'https://api.cisco.com/bug/v2.0/bugs/bug_ids/'

CLIENT_ID = 'edatpdtwgvn5scwv23mcdnqs'
CLIENT_SECRET = 'YPTJDBZ5MMBudUh6HSwcQCqx'

# Auth function
def get_auth_token():
    auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    auth_payload = {'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'client_credentials'}
    auth_response = requests.post(AUTH_API_URL, data=auth_payload, headers=auth_headers)
    auth_response.raise_for_status()
    if auth_response.status_code == 200:
        auth_json_data = auth_response.json()
        auth_token_type = auth_json_data['token_type']
        auth_access_token = auth_json_data['access_token']
        return auth_token_type+' '+auth_access_token
    return None


# Bug API function
def get_bug_api(bug_id):
    """Get a response from Cisco Hello API and return it as a string.
    Functions for Soundhound, Google, IBM Watson, or other APIs can be added
    to create the desired functionality into this bot.
    """
    requests.packages.urllib3.disable_warnings()
    
    headers = {'Accept': 'application/json', 'Authorization': get_auth_token()}
    response = requests.get(BUG_API_URL+bug_id, headers=headers, verify=False)
    response.raise_for_status()
    if response.status_code == 200:
        json_data = response.json()
        return json_data['bugs'][0]['headline'], json_data['bugs'][0]['description']


def cmd_bug(params):
    """**/bug <defect>** - return information for defect"""
    print("FOUND '/bug'")
    bug_id = params['message'].text.split()[1].strip()
    # Get a response
    bug_headline, bug_description = get_bug_api(bug_id)
    print("SENDING RESPONSE FROM HELLO API '{}'".format(bug_headline))
    # Post the response to the room where the request was received
    results = list()
    results.append('**'+bug_id+': '+bug_headline+'**')
    results.append('- - -')
    results.append(bug_description)
    return results


def cmd_help(params):
    """**/help** - print list of supported commands"""
    results = []
    for obj in globals():
        if 'cmd_' in obj and obj is not 'cmd_default':
            results.append(globals()[obj].__doc__)
    return results
