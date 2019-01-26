#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""Marketing bot to run on CLEUR lab 2293
"""


# Use future for Python v2 and v3 compatibility
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
from builtins import *

import yaml
import logging
import os,sys,inspect
from typing import Dict, Any
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

# To be able to load modules from parent directory
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from utils import setinitial
from utils import PSQL_marketing

from bi_template import *


# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)

config = {}  # create dictionary for config
try:
    config = setinitial.setup_config('config/config_marketing.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)

def process_message(api: WebexTeamsAPI, config:Dict, json_data) -> str:
    # Create a Webhook object from the JSON data
    webhook_obj = Webhook(json_data)
    # Get the room details
    room = api.rooms.get(webhook_obj.data.roomId)
    # Get the message details
    message = api.messages.get(webhook_obj.data.id)
    # Get the sender's details
    person = api.people.get(message.personId)

    try:
        psql_obj = PSQL_marketing.PSQL('ciscolive', config["db_host"],
                             config["db_login"], config["db_password"])
    except IndexError:
        logger.fatal(f'Can\'t connect to Database:{config["db_login"]}@{config["db_host"]}/ciscolive')
        exit(2)

    logger.info(f'Connected to DB:{config["db_login"]}@{config["db_host"]}/ciscolive')

    # If needed runs of the tasks has completed
    if is_enough(psql_obj):
        api.messages.create(room.id, text="Marketing campaign is over. Please wait for organisators to contact")
        return 'OK'

    # loop prevention control step.
    # If you respond to all messages...  You will respond to the messages
    # that the bot posts and thereby create a loop condition.
    me = api.people.me()
    if message.personId == me.id:
        # Message was sent by me (bot); do not respond.
        logger.info(f'Found message sent to me. Do not respond')
        return 'OK'

    else:
        # Message was sent by someone else; parse message and respond.
        params = dict()
        params['person'] = person
        params['room'] = room
        params['message'] = message
        params['psql_obj'] = psql_obj
        results = process_command(params)
        for result in results:
            # Post the response to the room where the request was received
            api.messages.create(room.id, markdown=result)
        return 'OK'


def process_command(params):

    try:
        if len(params['message'].files) > 0:
            # User send us photo in attach
            return process_received_photo(params)
    except TypeError as e:
        logger.info('Not found attached photo, proceeding with commands parsing')

    command = params['message'].text.lower.split()[0]
    logger.info(f'command={command}')

    if command[0] == '/' and f'cmd_{command[1:]}' in globals():
        # User send us command
        return globals()[f'cmd_{command[1:]}'](params)
    elif command.strip()[0:4] == 'http':
        # User send us link to the social network
        return process_received_links(params)
    elif 'cmd_default' in globals():
        return globals()['cmd_default'](params)
    else:
        return ['Invalid command. Please use /help for list of commands.']
