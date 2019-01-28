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

import yaml
import logging

from scripts import setinitial
from scripts import PSQL_marketing

# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)



import sched
import time
from webexteamssdk import WebexTeamsAPI
from random import shuffle
from dates import *
import json

from bot import assign_new_task
from bot import prepare_markdown_quiz_task
from bot import is_enough
from scripts.tasker_marketing import Tasker

try:
    config = setinitial.setup_config('config/config_marketing.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)

scheduler = sched.scheduler(time.time, time.sleep)
api = WebexTeamsAPI( access_token=config['bot_access_token'])

def assign_new_tasks(psql_obj):
    all_persons = Tasker.get_all_users(psql_obj)

    for person in all_persons:
        person_name = person['name']
        person_surname = person['surname']
        person_email =person['email']
        person_id = person['id']
        room_id = person['room_id']

        logger.info(f'Get user:{person_name};{person_surname};({person_email});'
                    f'person_id:{person_id};person_roomid:{room_id}')

        # Get current task_id and check status of the task (approved or rejected)
        task_id = Tasker.has_task(psql_obj, person_id)
        if Tasker.get_task_status_by_person_id(psql_obj,person_id,task_id):
            # Previous task was approved
            api.messages.create(room_id, text="Your previous message was approved",
                                markdown="Your previous message was **approved**")
        else:
            # Previous task was rejected
            api.messages.create(room_id, text="Your previous message was approved",
                                markdown="Your previous message was **rejected**")

        if is_enough(psql_obj):
            # Check if the marketing campaign is over
            api.messages.create(room_id, text="Marketing campaign is over. Please wait for organisators to contact")
        else:

            task_dict = {}  # dictionary structure for the task
            try:
                task_dict = assign_new_task(psql_obj, person_id)
                Tasker.increment_task_run(psql_obj)
            except RuntimeError:
                # Error in addition to assigned_tasks table
                pass
                return 'NOK'
            except KeyError:
                # User have answered all the question that we have
                api.messages.create(room_id, text="You have answered all the question that we have",
                                    markdown="You have answered all the question that we have")
                return 'OK'

            logger.info(f'{person_id} Sending task')
            api.messages.create(room_id, text=f"The {task_dict['task_number']} question for you:",
                                markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))


def notify_all_users(psql_obj,time_left):
    all_persons = Tasker.get_all_users(psql_obj)

    for person in all_persons:
        person_name = person['name']
        person_surname = person['surname']
        person_email =person['email']
        person_id = person['id']
        room_id = person['room_id']

        logger.info(f'Get user:{person_name};{person_surname};({person_email});'
                    f'person_id:{person_id};person_roomid:{room_id}')

        api.messages.create(room_id, text=f'{time.ctime(now)} -> {time_left}sec left till next task!!!',
                                markdown=f'{time.ctime(now)} -> **{time_left}sec** left till next task!!!')

def print_event(name):
    print('EVENT:', time.ctime(time.time()), name)

if __name__ == '__main__':

    try:
        psql_obj = PSQL_marketing.PSQL('ciscolive', config["db_host"],
                             config["db_login"], config["db_password"])
    except IndexError:
        logger.fatal(f'Can\'t connect to Database:{config["db_login"]}@{config["db_host"]}/ciscolive')
        exit(2)

    logger.info(f'Connected to DB:{config["db_login"]}@{config["db_host"]}/ciscolive')

    now = time.time()
    logger.info(f'START:{time.ctime(now)}')

    #for i in range(0, config['marketing_runs']):
    #    scheduler.enterabs(now+i*10+5, 2, print_event, ('first',))
    #    scheduler.enterabs(now+i*10+9, 1, print_event, ('second',))

    for i in range(0,config['marketing_runs']+1):
        logger.info(f'Creating scheduler for run:{str(i)}')
        run_interval = config['interval_runs']
        scheduler.enterabs(now + run_interval*i,2,assign_new_tasks,(psql_obj,))

        # For debugging notify how much time left
        first_notify = run_interval/2 # 30 secs - each triggered time
        second_notify = run_interval - 10 # 50 secs - each triggered time

        scheduler.enterabs(now + run_interval*i + first_notify, 1,
                           notify_all_users,(psql_obj,run_interval-first_notify))
        scheduler.enterabs(now + run_interval*i + second_notify, 1,
                           notify_all_users,(psql_obj,run_interval-second_notify))
#
    #assign_new_tasks(psql_obj)
    scheduler.run()
