from webexteamssdk import WebexTeamsAPI, Webhook
from flask import Flask, request
from builtins import *
import sys
import requests
from urllib.parse import urljoin

# Initialize the environment
# Create the web application instance
flask_app = Flask(__name__)
# Create the Webex Teams API connection object

# You need to change bot access token to the value provided by Pinacolada bot
bot_access_token = 'SAMPLE'

# Constants
NGROK_CLIENT_API_BASE_URL = "http://localhost:4040/api"
WEBHOOK_NAME = "webhook_samplebot"
WEBHOOK_URL_SUFFIX = "/events"
WEBHOOK_RESOURCE = "messages"
WEBHOOK_EVENT = "created"

try:
    assert(bot_access_token!='SAMPLE')
except AssertionError:
    print('Fatal: Please change \'bot_access_token\' variable in bot-sample.py to the value provided by Pinacolada bot')
    exit(-1)

# Core bot functionality
# Your Webex Teams webhook should point to http://<serverip>:5000/events
@flask_app.route('/events', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/events' URI."""

    if request.method == 'GET':
        return ("""<!DOCTYPE html><html lang="en">
                       <head><meta charset="UTF-8"><title>ServiceBot</title></head>
                        <body>
                            <p><strong>ServiceBot</strong></p>
                        </body>
                   </html>""")
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

            if message.text.lower().startswith("/echo "):
                api_response = 'Echoing back to you: {}'.format(message.text[6:])
                api.messages.create(room.id, text=api_response)

            elif message.text.lower() == "/whoami":
                api_response = 'I know who you are:\n' \
                               'room_name = {}\n' \
                               'your First Name = {}\n' \
                               'your Last Name = {}\n' \
                               ''.format(room.title, person.firstName, person.lastName, person.emails)

                print("SENDING RESPONSE TO A CLIENT '{}'".format(message.personId))
                # Post the response to the room where the request was received
                api.messages.create(room.id, text=api_response)

                for email in person.emails:
                    #print("email = {}".format(email))
                    api_response = "email = {}".format(email)
                    api.messages.create(room.id, text=api_response)

            else:
                api_response = 'The command you\'ve sent isn\'t supported! \n' \
                               'List of supported commands:\n' \
                               '1. /whoami - shows detailed info about you\n' \
                               '2. /echo [text] - echoes back [text] that you sent to me\n'

                api.messages.create(room.id, text=api_response)

    return 'OK'


def get_ngrok_public_url():
    """Get the ngrok public HTTP URL from the local client API."""
    try:
        response = requests.get(url=NGROK_CLIENT_API_BASE_URL + "/tunnels",
                                headers={'content-type': 'application/json'})
        response.raise_for_status()

    except requests.exceptions.RequestException:
        print("Could not connect to the ngrok client API; "
              "assuming not running.")
        return None

    else:
        for tunnel in response.json()["tunnels"]:
            if tunnel.get("public_url", "").startswith("http://"):
                print('Found ngrok public HTTP URL:{}'.format(tunnel["public_url"]))
                return tunnel["public_url"]

def get_ngrok_port():
    """Get the ngrok public HTTP URL from the local client API."""
    try:
        response = requests.get(url=NGROK_CLIENT_API_BASE_URL + "/tunnels",
                                headers={'content-type': 'application/json'})
        response.raise_for_status()

    except requests.exceptions.RequestException:
        print("Could not connect to the ngrok client API; "
              "assuming not running.")
        return None

    #print(response.json())
    #print(response.json()['tunnels']['config']['addr'])
    tunnel0_config = response.json()["tunnels"][0]['config']
    ngrok_port = tunnel0_config['addr'].split(':')[2]

    return ngrok_port

def delete_webhooks_with_name(api, name):
    """Find a webhook by name."""
    for webhook in api.webhooks.list():
        if webhook.name == name:
            print('Deleting Webhook: {}{}'.format(webhook.name,webhook.targetUrl))
            api.webhooks.delete(webhook.id)


def create_ngrok_webhook(api, ngrok_public_url, WEBHOOK_NAME):
    """Create a Webex Teams webhook pointing to the public ngrok URL."""
    print('Creating Webhook...{}'.format(WEBHOOK_NAME))
    webhook = api.webhooks.create(
        name=WEBHOOK_NAME,
        targetUrl=urljoin(ngrok_public_url, WEBHOOK_URL_SUFFIX),
        resource=WEBHOOK_RESOURCE,
        event=WEBHOOK_EVENT,
    )
    print(webhook)
    print("Webhook successfully created.")
    return webhook


def create_webhook(api, WEBHOOK_NAME):
    """Delete previous webhooks. If local ngrok tunnel, create a webhook."""

    delete_webhooks_with_name(api, name=WEBHOOK_NAME)
    public_url = get_ngrok_public_url()
    if public_url is not None:
        create_ngrok_webhook(api, public_url, WEBHOOK_NAME)
        return True
    else:
        return False

if __name__ == '__main__':
    api = WebexTeamsAPI(bot_access_token)

    """Delete previous webhooks. If local ngrok tunnel, create a webhook."""
    if create_webhook(api,WEBHOOK_NAME):
        ngrok_port = get_ngrok_port()
        print('Get ngrok port={}.Starting Flask server on it'.format(ngrok_port))

        # Start the Flask web server
        flask_app.run(host='0.0.0.0', port=ngrok_port)
    else:
        print('Can\'t create webhook for WebexTeams')