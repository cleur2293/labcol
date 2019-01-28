import webhook as webhook
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

bot_access_token = 'SAMPLE'
webhook_name = "ngrok_webhook"

#
#
#
#
#<put code for main business logic of rhe bot here>
#
#
#
#
#

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
    ngrok_port = tunnel0_config['addr'].split(':')[1]

    return ngrok_port

def delete_webhooks_with_name(api, name):
    """Find a webhook by name."""
    for webhook in api.webhooks.list():
        if webhook.name == name:
            print('Deleting Webhook:{}{}'.format(webhook.name,webhook.targetUrl))
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
    if create_webhook(api,webhook_name):
        ngrok_port = get_ngrok_port()
        print('Get ngrok port={}.Starting Flask server on it'.format(ngrok_port))

        # Start the Flask web server
        flask_app.run(host='0.0.0.0', port=ngrok_port)
    else:
        print('Can\'t create webhook for WebexTeams')