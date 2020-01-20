#!/usr/bin/env python3
#  -*- coding: utf-8 -*-
"""Sample script to read local ngrok info and create a corresponding webhook.
Sample script that reads ngrok info from the local ngrok client api and creates
a Webex Teams Webhook pointint to the ngrok tunnel's public HTTP URL.
Typically ngrok is called run with the following syntax to redirect an
Internet accesible ngrok url to localhost port 8080:
    $ ngrok http 8080
To use script simply launch ngrok, and then launch this script.  After ngrok is
killed, run this script a second time to remove webhook from Webex Teams.
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
from builtins import *
import sys

from webexteamssdk import WebexTeamsAPI
import requests
from urllib.parse import urljoin

import logging
logger = logging.getLogger(__name__) # Creating logger for logging across this module

# Constants
NGROK_CLIENT_API_BASE_URL = "http://localhost:4040/api"
WEBHOOK_NAME = "ngrok_webhook"
WEBHOOK_URL_SUFFIX = "/events"
WEBHOOK_URL_SUFFIX2 = "/memberships"
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

    #print(response.json())
    #print(response.json()['tunnels']['config']['addr'])
    tunnel0_config = response.json()["tunnels"][0]['config']
    ngrok_port = tunnel0_config['addr'].split(':')[2]

    return ngrok_port

def delete_webhooks_with_name(api, name):
    """Find a webhook by name."""
    for webhook in api.webhooks.list():
        if webhook.name == name or True:
            # True to delete all webhooks
            logger.info(f'Deleting Webhook:{webhook.name} {webhook.targetUrl}')
            api.webhooks.delete(webhook.id)


def create_ngrok_webhook(api, ngrok_public_url, webhook_name, memberships_resource=''):
    """Create a Webex Teams webhook pointing to the public ngrok URL."""

    if memberships_resource == '':
        logger.info(f'Creating Webhook for messages resource...{webhook_name}')
        webhook = api.webhooks.create(
            name=webhook_name,
            targetUrl=urljoin(ngrok_public_url, WEBHOOK_URL_SUFFIX),
            resource=WEBHOOK_RESOURCE,
            event=WEBHOOK_EVENT,
        )
    else:
        logger.info(f'Creating Webhook for memberships resource...{webhook_name}')
        webhook = api.webhooks.create(
            name=webhook_name,
            targetUrl=urljoin(ngrok_public_url, WEBHOOK_URL_SUFFIX2),
            resource='memberships',
            event=WEBHOOK_EVENT,
        )
    logger.info(webhook)
    logger.info("Webhook successfully created.")
    return webhook


def create_webhook(api: WebexTeamsAPI, webhook_name:str) -> bool:
    """Delete previous webhooks. If local ngrok tunnel, create a webhook."""


    delete_webhooks_with_name(api, name=webhook_name)
    public_url = get_ngrok_public_url()
    if public_url is not None:
        create_ngrok_webhook(api, public_url, webhook_name)

        create_ngrok_webhook(api, public_url, webhook_name + '_memberships','memberships')
        return True
    else:
        return False


if __name__ == '__main__':
    main()
