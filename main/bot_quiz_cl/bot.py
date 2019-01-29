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
from time import sleep
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

# To be able to load modules from parent directory
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from utils import setinitial
from utils import PSQL

from bi_template import *


# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)

config = {}  # create dictionary for config
try:
    config = setinitial.setup_config('config/config_quiz_cl.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)

def process_message(api: WebexTeamsAPI, config:Dict, json_data, psql_obj) -> str:
    # Create a Webhook object from the JSON data
    webhook_obj = Webhook(json_data)
    # Get the room details
    room = api.rooms.get(webhook_obj.data.roomId)
    # Get the message details

    message = api.messages.get(webhook_obj.data.id)
    logger.info(f'message text received:{message.text}')
    # Get the sender's details
    person = api.people.get(message.personId)


    # loop prevention control step.
    # If you respond to all messages...  You will respond to the messages
    # that the bot posts and thereby create a loop condition.
    me = api.people.me()
    if message.personId == me.id:
        # Message was sent by me (bot); do not respond.
        logger.info(f'Found message sent to me. Do not respond')
        return 'OK'

    elif room.type == 'group':
        # If bot mentioned in group
        api.messages.create(room.id, markdown='Let\'s not spam into that room, '
                                              'just click my icon and send **/start** to start an amazing quiz!')
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

            if type(result) != list:
                # This is normal string, send it to the user
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown=result)
            else:
                # This result is the list that means that second attachment is picture
                # Post the response to the room where the request was received
                # Trying to attach picture to the message

                try:
                    api.messages.create(room.id, markdown=result[0], files=result[1])
                except (ValueError,IndexError):
                    logger.error(f'{message.personId}:Can\'t open file to attach:{result[1]}')
                    api.messages.create(room.id,
                                       markdown=f'<<Error: Can\'t open file to attach:{result[1]}>>')
                    api.messages.create(room.id, markdown=result[0])

        return 'OK'

def welcome_message(api: WebexTeamsAPI, config:Dict, json_data) -> str:
    # Create a Webhook object from the JSON data
    webhook_obj = Webhook(json_data)
    # Get the room details
    room = api.rooms.get(webhook_obj.data.roomId)
    # Get the message details


    logger.info('sleeping 5 sec')
    sleep(5)

    if room.type == 'group':
        logger.info('membership message received in group message, sending welcome message')
        api.messages.create(room.id, markdown="Hey! I'm quiz bot sitting in that room. Click my icon and send **/start** to start an amazing quiz!")
        api.messages.create(room.id, markdown="> Want to make the same bot? Take the lab **LABCOL-2293 at WISP** (we are just in front of the clinic)")
    else:
        logger.info('membership message received in direct message, ignoring it')

    return 'OK'

def process_command(params):

    try:
        if len(params['message'].files) > 0:
            # User send us photo in attach, we don't support attachment receive
            return attachment_not_supported(params)
    except TypeError as e:
        logger.info('Not found attached photo, proceeding with commands parsing')

    command = params['message'].text.lower().split()[0]
    logger.info(f'command={command}')

    if command[0] == '/' and f'cmd_{command[1:]}' in globals():
        # User send us command
        return globals()[f'cmd_{command[1:]}'](params)
    elif command.strip() in '123456789' and has_tech(params['psql_obj'],params['message'].personId):
        # User send us link to the social network
        return process_input_digit(params)
    elif command.strip() in '123456789' and not has_tech(params['psql_obj'],params['message'].personId):
        # User send us link to the social network
        return choose_tech(params)
    else:
        return cmd_default(params)
