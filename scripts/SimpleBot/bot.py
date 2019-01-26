#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""A simple bot script, built on Flask.
This sample script leverages the Flask web service micro-framework
(see http://flask.pocoo.org/).  By default the web server will be reachable at
port 5000 you can change this default if desired (see `flask_app.run(...)`).
ngrok (https://ngrok.com/) can be used to tunnel traffic back to your server
if your machine sits behind a firewall.
You must create a Webex Teams webhook that points to the URL where this script
is hosted.  You can do this via the WebexTeamsAPI.webhooks.create() method.
Additional Webex Teams webhook details can be found here:
https://developer.webex.com/webhooks-explained.html
A bot must be created and pointed to this server in the My Apps section of
https://developer.webex.com.  The bot's Access Token should be added as a
'WEBEX_TEAMS_ACCESS_TOKEN' environment variable on the web server hosting this
script.
This script supports Python versions 2 and 3.
Copyright (c) 2016-2018 Cisco and/or its affiliates.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


# Use future for Python v2 and v3 compatibility
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import builtins


__author__ = "Chris Lunsford"
__author_email__ = "chrlunsf@cisco.com"
__contributors__ = ["Brad Bester <brbester@cisco.com>"]
__copyright__ = "Copyright (c) 2016-2018 Cisco and/or its affiliates."
__license__ = "MIT"


from flask import Flask, request
import requests

from webexteamssdk import WebexTeamsAPI, Webhook


# Module constants
# Module constants
AUTH_API_URL = 'https://cloudsso.cisco.com/as/token.oauth2'
HELLO_API_URL = 'https://api.cisco.com/hello'
BUG_API_URL = 'https://api.cisco.com/bug/v2.0/bugs/bug_ids/'

CLIENT_ID = 'c6vfxn47gs8du5qhgya77que'
CLIENT_SECRET = '8qCgCxuyBFkx5HkzhEuqwrZ6'


# Initialize the environment
# Create the web application instance
flask_app = Flask(__name__)
# Create the Webex Teams API connection object
api = WebexTeamsAPI(access_token='MTVmMGE3Y2YtYzdiNi00ZGI2LTgzYjUtMjg2ZmNhMzEwZTM1MmZiNWQyOGItZWEy_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f')

# Auth function
def get_auth_token():
    auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    auth_payload = {'client_id': CLIENT_ID,'client_secret': CLIENT_SECRET, 'grant_type': 'client_credentials'}
    auth_response = requests.post(AUTH_API_URL, data = auth_payload, headers = auth_headers)
    auth_response.raise_for_status()
    if auth_response.status_code == 200:
        auth_json_data = auth_response.json()
        auth_token_type = auth_json_data['token_type']
        auth_access_token = auth_json_data['access_token']
        return auth_token_type+' '+auth_access_token
    return None

# Hello API function
def get_hello_api():
    """Get a response from Cisco Hello API and return it as a string.
    Functions for Soundhound, Google, IBM Watson, or other APIs can be added
    to create the desired functionality into this bot.
    """
    headers = {'Accept': 'application/json', 'Authorization': get_auth_token()}
    response = requests.get(HELLO_API_URL, headers=headers, verify=False)
    response.raise_for_status()
    if response.status_code == 200:
        json_data = response.json()
        return json_data['helloResponse']['response']

# Bug API function
def get_bug_api(bug_id):
    """Get a response from Cisco Hello API and return it as a string.
    Functions for Soundhound, Google, IBM Watson, or other APIs can be added
    to create the desired functionality into this bot.
    """
    headers = {'Accept': 'application/json', 'Authorization': get_auth_token()}
    response = requests.get(BUG_API_URL+bug_id, headers=headers, verify=False)
    response.raise_for_status()
    if response.status_code == 200:
        json_data = response.json()
        return json_data['bugs'][0]['headline'], json_data['bugs'][0]['description']

# Core bot functionality
# Your Webex Teams webhook should point to http://<serverip>:5000/events
@flask_app.route('/events', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/events' URI."""
    if request.method == 'GET':
        return ("""<!DOCTYPE html>
                   <html lang="en">
                       <head>
                           <meta charset="UTF-8">
                           <title>Webex Teams Bot served via Flask</title>
                       </head>
                   <body>
                   <p>
                   <strong>Your Flask web server is up and running!</strong>
                   </p>
                   <p>
                   Here is a nice Cat Fact for you:
                   </p>
                   <blockquote>{}</blockquote>
                   </body>
                   </html>
                """.format(get_hello_api()))
    elif request.method == 'POST':
        """Respond to inbound webhook JSON HTTP POST from Webex Teams."""

        # Get the POST data sent from Webex Teams
        json_data = request.json
        print("\n")
        print("WEBHOOK POST RECEIVED:")
        print(json_data)
        print("\n")

        # Create a Webhook object from the JSON data
        webhook_obj = Webhook(json_data)
        # Get the room details
        room = api.rooms.get(webhook_obj.data.roomId)
        # Get the message details
        message = api.messages.get(webhook_obj.data.id)
        # Get the sender's details
        person = api.people.get(message.personId)

        print("NEW MESSAGE IN ROOM '{}'".format(room.title))
        print("FROM '{}'".format(person.displayName))
        print("MESSAGE '{}'\n".format(message.text))

        # This is a VERY IMPORTANT loop prevention control step.
        # If you respond to all messages...  You will respond to the messages
        # that the bot posts and thereby create a loop condition.
        me = api.people.me()
        if message.personId == me.id:
            # Message was sent by me (bot); do not respond.
            return 'OK'

        else:
            # Message was sent by someone else; parse message and respond.
            if "/HELLO" in message.text:
                print("FOUND '/HELLO'")
                # Get a response
                api_response = get_hello_api()
                print("SENDING RESPONSE FROM HELLO API '{}'".format(api_response))
                # Post the response to the room where the request was received
                api.messages.create(room.id, text=api_response)
            elif "/BUG" in message.text:
                print("FOUND '/BUG'")
                bug_id = message.text.split('/BUG')[1].strip()
                # Get a response
                bug_headline, bug_description = get_bug_api(bug_id)
                print("SENDING RESPONSE FROM HELLO API '{}'".format(bug_headline))
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown='**'+bug_id+': '+bug_headline+'**')
                api.messages.create(room.id, markdown='- - -')
                api.messages.create(room.id, text=bug_description)
            return 'OK'


if __name__ == '__main__':
    # Start the Flask web server
    flask_app.run(host='0.0.0.0', port=5000)