from webexteamssdk import WebexTeamsAPI
import requests
from urllib.parse import urljoin

import logging
logger = logging.getLogger(__name__) # Creating logger for logging across this module

# Constants
NGROK_CLIENT_API_BASE_URL = "http://localhost:4040/api"
WEBHOOK_NAME = "ngrok_webhook"
WEBHOOK_URL_SUFFIX = "/events"
WEBHOOK_RESOURCE = "messages"
WEBHOOK_EVENT = "created"


def get_ngrok_public_url():
    """Get the ngrok public HTTP URL from the local client API."""
    try:
        response = requests.get(url=NGROK_CLIENT_API_BASE_URL + "/tunnels",
                                headers={'content-type': 'application/json'})
        response.raise_for_status()

    except requests.exceptions.RequestException:
        logger.info("Could not connect to the ngrok client API; "
              "assuming not running.")
        return None

    else:
        for tunnel in response.json()["tunnels"]:
            if tunnel.get("public_url", "").startswith("http://"):
                logger.info(f'Found ngrok public HTTP URL:{tunnel["public_url"]}')
                return tunnel["public_url"]

def get_ngrok_port():
    """Get the ngrok public HTTP URL from the local client API."""
    try:
        response = requests.get(url=NGROK_CLIENT_API_BASE_URL + "/tunnels",
                                headers={'content-type': 'application/json'})
        response.raise_for_status()

    except requests.exceptions.RequestException:
        logger.info("Could not connect to the ngrok client API; "
              "assuming not running.")
        return None

    tunnel0_config = response.json()["tunnels"][0]['config']
    ngrok_port = tunnel0_config['addr'].split(':')[1]

    return ngrok_port

def delete_webhooks_with_name(api, name):
    """Find a webhook by name."""
    for webhook in api.webhooks.list():
        if webhook.name == name or webhook.name == 'webhook_santa':
            logger.info(f'Deleting Webhook:{webhook.name}{webhook.targetUrl}')
            api.webhooks.delete(webhook.id)


def create_ngrok_webhook(api, ngrok_public_url, webhook_name):
    """Create a Webex Teams webhook pointing to the public ngrok URL."""
    logger.info(f'Creating Webhook...{webhook_name}')
    webhook = api.webhooks.create(
        name=webhook_name,
        targetUrl=urljoin(ngrok_public_url, WEBHOOK_URL_SUFFIX),
        resource=WEBHOOK_RESOURCE,
        event=WEBHOOK_EVENT,
    )
    logger.info(webhook)
    logger.info("Webhook successfully created.")
    return webhook


def create_webhook(webhook_name, access_token):
    """Delete previous webhooks. If local ngrok tunnel, create a webhook."""
    api = WebexTeamsAPI(access_token)
    delete_webhooks_with_name(api, webhook_name)
    public_url = get_ngrok_public_url()
    if public_url is not None:
        create_ngrok_webhook(api, public_url, webhook_name)

    ngrok_port = get_ngrok_port()
    logger.info(f'Get ngrok port={ngrok_port}')

    return ngrok_port
