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
import logging
from typing import Dict, Any

from scripts import setinitial
from scripts import PSQL
from scripts.tasker import Person, All_persons, Tasker


# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)



from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room


# Module constants
CAT_FACTS_URL = 'https://catfact.ninja/fact'


config = {}  # create dictionary for config
try:
    config = setinitial.setup_config()  # populate config from yaml file
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


#"""
Persons = All_persons(
    {'Y2lzY29zcGFyazovL3VzL1dFQkhPT0svNDNkNDQ0Y2YtYmZlNi00ZjcxLWJmMmUtYmQ4MDQ2MjFlMTZj':
    Person(
        'Y2lzY29zcGFyazovL3VzL1dFQkhPT0svNDNkNDQ0Y2YtYmZlNi00ZjcxLWJmMmUtYmQ4MDQ2MjFlMTZj',
        'Alexey',
        'Sazhin',
        'asazhin@cisco.com'
           )
    }
)
#"""
#Persons = All_persons()


# Helper functions
def get_catfact():
    """Get a cat fact from catfact.ninja and return it as a string.
    Functions for Soundhound, Google, IBM Watson, or other APIs can be added
    to create the desired functionality into this bot.
    """
    response = requests.get(CAT_FACTS_URL, verify=False)
    response.raise_for_status()
    json_data = response.json()
    return json_data['fact']

def create_webhook_obj(request_json: str) -> Webhook:
    # Get the POST data sent from Webex Teams
    json_data = request_json
    logger.info("WEBHOOK POST RECEIVED:")
    logger.info(json_data)

    # Create a Webhook object from the JSON data

    return Webhook(json_data)

def process_message(api: WebexTeamsAPI, message:Message, room:Room) -> str:
    try:
        psql_obj = PSQL.PSQL('ciscolive', config["db_host"],
                             config["db_login"], config["db_password"])
    except IndexError:
        logger.fatal(f'Can\'t connect to Database:{config["db_login"]}@{config["db_host"]}/ciscolive')
        exit(2)

    logger.info(f'Connected to DB:{config["db_login"]}@{config["db_host"]}/ciscolive')

    if "/CAT" in message.text:
        logger.info("FOUND '/CAT'")
        # Get a cat fact
        cat_fact = get_catfact()
        logger.info("SENDING CAT FACT '{}'".format(cat_fact))
        # Post the fact to the room where the request was received
        api.messages.create(room.id, text=cat_fact)

        return 'OK'

    elif "/TEST" in message.text:
        logger.info("FOUND '/TEST'")
        return 'OK'

    elif "/START" in message.text:
        logger.info("FOUND '/START'")


        # check if that users exists
        if psql_obj.is_person_exists(message.personId):
            logger.info("This is existing user")

            # check if that user already has task assigned
            has_task = Tasker.has_task(psql_obj,message.personId)

            logger.info(has_task)
            api.messages.create(room.id, text="You already have the task. Please answer it first",
                                markdown="You already have the task. Please answer it first")

            task = Tasker.get_assigned_task_by_id(psql_obj, message.personId,has_task)
            api.messages.create(room.id, text="Your current task:",
                            markdown=prepare_markdown_quiz_task(task))

        # user does not exist, create it and assign the task
        else:
            logger.info("This is new user")
            api.messages.create(room.id, text="You are new user", markdown="You are **new** user)")

            #Creating new user
            person_name = api.people.get(message.personId).firstName
            person_surname = api.people.get(message.personId).lastName

            Persons.addPerson(message.personId,person_name,person_surname,message.personEmail)

            if psql_obj.add_person(message.personId,person_name,person_surname,message.personEmail):
                logger.info('Created user successfully')

                task = Tasker.get_random_task(psql_obj)

                logger.info(task)

                api.messages.create(room.id, text="The first question for you:",
                                    markdown=prepare_markdown_quiz_task(task))

                # TODO: we are not randomizing tasks' answer list now
                if Tasker.assign_task(psql_obj, message.personId ,task["id"], task["answer"]):
                    logger.info("Added task to the assigned_tasks table successfully")
                else:
                    logger.info("Error in addition to assigned_tasks table")

            else:
                logger.error('User creation failed')


        return 'OK'


    elif message.text in "12345678":
        logger.info("FOUND '[digit]'")

        api.messages.create(room.id, text=message.text, markdown="Thank you, your answer was accepted")


        assign_new_task(api,psql_obj,room,message)

        return 'OK'

def assign_new_task(api,psql_obj,room,message) -> bool:

    # TODO increment task id in message to the customer (now it 'first' only)

    task = Tasker.get_random_task(psql_obj)
    api.messages.create(room.id, text="The $first$ question for you:",
                        markdown=prepare_markdown_quiz_task(task))

    # TODO: we are not randomizing tasks' answer list now
    if Tasker.assign_task(psql_obj, message.personId, task["id"], task["answer"]):
        logger.info("Added task to the assigned_tasks table successfully")
    else:
        logger.info("Error in addition to assigned_tasks table")
        return False

    return True

def prepare_markdown_quiz_task(task: Dict) -> str:

    result_str = f'The first question for you:<br/> {task["task"]}<br/>'

    i = 1 # options' counter

    for option in task["variants"]:
      result_str += f'{i}. {option}<br/>'
      i += 1

    result_str += f'Choose your answer (1 to {i-1}):'

    return result_str




# Core bot functionality
# Your Webex Teams webhook should point to http://<serverip>:5000/events
#@flask_app.route('/events', methods=['GET', 'POST'])
@flask_app.route('/messages', methods=['GET', 'POST'])
def webex_teams_webhook_messages():
    logger.info("TEST")
    return True

@flask_app.route('/', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/' URI."""
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
                """.format(get_catfact()))
    elif request.method == 'POST':
        """Respond to inbound webhook JSON HTTP POST from Webex Teams."""


        webhook_obj = create_webhook_obj(request.json)
        # Get the room details
        room = api.rooms.get(webhook_obj.data.roomId)
        # Get the message details
        message = api.messages.get(webhook_obj.data.id)
        #webhook_obj.data.roomId = 'group' # 'direct'
        # Get the sender's details
        person = api.people.get(message.personId)

        logger.info("NEW MESSAGE IN ROOM '{}'".format(room.title))
        logger.info("FROM '{}'".format(person.displayName))
        logger.info("MESSAGE '{}'".format(message.text))

        # This is a VERY IMPORTANT loop prevention control step.
        # If you respond to all messages...  You will respond to the messages
        # that the bot posts and thereby create a loop condition.
        me = api.people.me()
        if message.personId == me.id:
            # Message was sent by me (bot); do not respond.
            return 'OK'

        else:
            # Message was sent by someone else; parse message and respond.
            return process_message(api,message,room)




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


    # Start the Flask web server
    flask_app.run(host='0.0.0.0', port=10010)