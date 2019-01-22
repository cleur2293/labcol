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
from builtins import *

from flask import Flask, request
import requests
import yaml
import os
import logging
from typing import Dict, Any
import urllib3

from scripts import setinitial
from scripts import PSQL_marketing
from scripts.tasker_marketing import Tasker


# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)



from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room


config = {}  # create dictionary for config
try:
    config = setinitial.setup_config('config/config_marketing.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)

# Initialize the environment
# Create the web application instance
flask_app = Flask(__name__)
# Create the Webex Teams API connection object
api = WebexTeamsAPI( access_token=config['bot_access_token'])

def req_message() -> str:
            message_files = ['https://api.ciscospark.com/v1/contents/Y2lzY29zcGFyazovL3VzL0NPTlRFTlQvMGI4ZTg3NjAtMWNkNi0xMWU5LWEyZmYtYjkxNzgzNDVlY2NjLzA']

            logger.error(f'Found attachment in user\'s input. Notifiying him that attachments are not supported')
            logger.error(f'message.files={message_files}')

            for file_url in message_files:
                logger.info(f'Accessing:{file_url}')
                response = sendWebexTeamsGET(file_url,config['bot_access_token'])
                content_disp = response.headers.get('Content-Disposition', None)
                logger.info('content_disp:{content_disp}')
                if content_disp is not None:
                    filename = content_disp.split("filename=")[1]
                    filename = filename.replace('"', '')
                    logger.info(f'result filename:{filename}')
                    with open(filename, 'wb') as f:
                        f.write(response.read())
                        logger.info(f'Saved-{filename}')
                else:
                    logger.info('Cannot save file- no Content-Disposition header received.')

            #api.messages.create(room.id, text="You can't send messages with attachments to me",
            #                   markdown="You can't send messages with attachments to me")

            return 'OK'

def sendWebexTeamsGET(url,bearer):
    http = urllib3.PoolManager()
    request = http.request('GET',url,
                            headers={"Accept" : "application/json",
                                     "Content-Type":"application/json",
                                     "Authorization": "Bearer " + bearer})
    #request.add_header("Authorization", "Bearer "+bearer)
    #contents = urllib3.urlopen(request)

    contents = request

    return contents



if __name__ == '__main__':

    """
    try:
        psql_obj = PSQL.PSQL('ciscolive', config["db_host"],
                            config["db_login"], config["db_password"])
    except IndexError:
        logger.fatal(f'Can\'t connect to Database:{config["db_login"]}@{config["db_host"]}/ciscolive')
        exit(2)

    logger.info(f'Connected to DB:{config["db_login"]}@{config["db_host"]}/ciscolive')

    rows = psql_obj.get_assigned_tasks()

    logger.info(rows)
    """

    req_message()
    print("END")

