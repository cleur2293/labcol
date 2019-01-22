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


# Helper functions

def create_webhook_obj(request_json: str) -> Webhook:
    # Get the POST data sent from Webex Teams
    json_data = request_json
    logger.info("WEBHOOK POST RECEIVED:")
    logger.info(json_data)

    # Create a Webhook object from the JSON data

    return Webhook(json_data)

def process_message(api: WebexTeamsAPI, message:Message, room:Room) -> str:
    try:
        psql_obj = PSQL_marketing.PSQL('ciscolive', config["db_host"],
                             config["db_login"], config["db_password"])
    except IndexError:
        logger.fatal(f'Can\'t connect to Database:{config["db_login"]}@{config["db_host"]}/ciscolive')
        exit(2)

    logger.info(f'Connected to DB:{config["db_login"]}@{config["db_host"]}/ciscolive')


    try:
        if len(message.files) > 0:

            logger.error(f'Found attachment in user\'s input. Notifiying him that attachments are not supported')
            logger.error(f'message.files={message.files}')

            for file_url in message.files:
                logger.info(f'Accessing:{file_url}')
                response = sendWebexTeamsGET(file_url,config['bot_access_token'])
                content_disp = response.headers.get('Content-Disposition', None)
                logger.info('content_disp:{content_disp}')
                if content_disp is not None:
                    filename = content_disp.split("filename=")[1]
                    filename = filename.replace('"', '')
                    logger.info('result filename:{filename}')
                    with open(filename, 'w') as f:
                        f.write(response.read())
                        logger.info('Saved-', filename)
                else:
                    logger.info('Cannot save file- no Content-Disposition header received.')

            api.messages.create(room.id, text="You can't send messages with attachments to me",
                                markdown="You can't send messages with attachments to me")
            return 'OK'
    except Exception as e:
        logger.info(e)

    if "/test" in message.text.lower():
        logger.info("FOUND '/test'")
        return 'OK'


    #if "/RERUN" in message.text:
    #    logger.info(f"FOUND '\/RERUN', deleting all the assigned tasks for the user: {message.personId}")


    #    return 'OK'

    elif "/start" in message.text.lower():
        logger.info(f'{message.personId}:FOUND "/start"')


        # check if that users exists
        if psql_obj.is_person_exists(message.personId):
            logger.info(f'{message.personId}:This is existing user')

            # check if that user already has task assigned
            has_task = Tasker.has_task(psql_obj,message.personId)

            logger.info(f'{message.personId}:That user has task? - {has_task}')

            if has_task:

                task_dict = {}  # dictionary structure for the task
                task_dict = get_current_task(psql_obj, message.personId, has_task)

                api.messages.create(room.id, text="You already have the task. Please answer it first",
                                markdown="You already have the task. Please answer it first")

                logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                                    markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

            else:

                logger.error(f'{message.personId}:We have that user'
                             f' in persons table, but don\'t have assigned tasks for him')
                logger.error(f'{message.personId}:Assigning task for him')

                #assign_new_task(api, psql_obj, room, message)

                task_dict = {} # dictionary structure for the task
                try:
                    task_dict = assign_new_task(psql_obj, message.personId)
                except RuntimeError:
                    #Error in addition to assigned_tasks table
                    pass
                    return 'NOK'
                except KeyError:
                    #User have answered all the question that we have
                    api.messages.create(room.id, text="You have answered all the question that we have",
                                    markdown="You have answered all the question that we have")
                    return 'OK'

                api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                                    markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))


        # user does not exist, create it and assign the task
        else:
            logger.info(f'{message.personId}:This is new user')
            api.messages.create(room.id, text="You are new user", markdown="You are **new** user")

            #Creating new user
            person_name = api.people.get(message.personId).firstName
            person_surname = api.people.get(message.personId).lastName

            if psql_obj.add_person(message.personId,person_name,person_surname,message.personEmail,message.roomId):
                logger.info(f'{message.personId}:User {message.personId} created user successfully')
                #assign_new_task(api, psql_obj, room, message)


                task_dict = {} # dictionary structure for the task
                try:
                    task_dict = assign_new_task(psql_obj, message.personId)
                except RuntimeError:
                    #Error in addition to assigned_tasks table
                    pass
                    return 'NOK'
                except KeyError:
                    #User have answered all the question that we have
                    api.messages.create(room.id, text="You have answered all the question that we have",
                                    markdown="You have answered all the question that we have")
                    return 'OK'

                logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                                        markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

            else:
                logger.error(f'{message.personId}:User {message.personId} creation failed')


        return 'OK'


    elif message.text in "123456789":
        logger.info(f'{message.personId}:FOUND "[digit]" in message:{message.text}')

        # If answer in range of the expected answers
        check_answer = check_answer_in_range(psql_obj, message.personId, int(message.text))

        is_enough_flag = is_enough(psql_obj, message.personId)
        is_answered_flag = answer_received_for_current_task(psql_obj, message.personId)

        if is_answered_flag and is_enough_flag:
            # If the user already completed all that tasks, we should not save answer from him

            logger.info(f'{message.personId}:User has already answered for'
                        f' all the questions. Letting him know about that')
            api.messages.create(room.id, text=message.text, markdown="You already answered all the tasks")


        # If user's answer is in expected range
        elif check_answer == 0:
            save_user_answer(psql_obj, message)

            api.messages.create(room.id, text=message.text, markdown="Thank you, your answer was accepted")

            # Check that user has answered all questions and we need to prepare report for him
            if is_enough_flag:
                report_dict = {}

                api.messages.create(room.id, text=message.text, markdown="You have completed the interview. "
                                                                         "Preparing score for you")
                report_dict = generate_report_dict(psql_obj, message.personId)

                api.messages.create(room.id, text=message.text, markdown="**Answered correctly:**")

                for correct_answer in report_dict['correct']:
                    task = Tasker.get_assigned_task_by_id(psql_obj, message.personId, correct_answer["task_id"])

                    api.messages.create(room.id, text=message.text, markdown=f'- {task["task"][0:20]}<...>')


                api.messages.create(room.id, text=message.text,
                                    markdown="**Answered incorrectly [your_answer -> right answer]:**")

                for wrong_answer in report_dict['wrong']:
                    task = Tasker.get_assigned_task_by_id(psql_obj, message.personId, wrong_answer["task_id"])
                    text = f'- {task["task"][0:20]}<...> [{wrong_answer["user_answer"]}->{wrong_answer["loc_answer"]}]'

                    #api.messages.create(room.id, text=message.text, markdown=f'{task["task"][0:20]}...')
                    api.messages.create(room.id, text=message.text, markdown=text)

            else:
                task_dict = {} # dictionary structure for the task
                try:
                    task_dict = assign_new_task(psql_obj, message.personId)
                except RuntimeError:
                    #Error in addition to assigned_tasks table
                    pass
                    return 'NOK'
                except KeyError:
                    #User have answered all the question that we have
                    api.messages.create(room.id, text="You have answered all the question that we have",
                                    markdown="You have answered all the question that we have")
                    return 'OK'

                if task_dict['files']:
                    # exception handling in case can't find attachment

                    logger.info(f'{message.personId}:Picture path is not null, '
                                f'trying to add picture as attachment:{task_dict["files"]}')

                    try:
                        api.messages.create(room.id, text="The {task_number} question for you:",
                                            markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']),
                                            files=task_dict['files'])
                    except ValueError:
                        logger.error(f'{message.personId}:Can\'t open file to attach:{task_dict["files"]}')

                        api.messages.create(room.id,
                                            markdown=f'<<Error: Can\'t open file to attach:{task_dict["files"]}>>')
                        api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                            markdown=prepare_markdown_quiz_task(task_dict,task_dict['task_number']))

                # If no attachment picture
                else:
                    logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                    api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                                        markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

        # If user doesn't have tasks assigned
        elif check_answer == -1:
            logger.info(f'{message.personId}:User does not have tasks assigned')
            api.messages.create(room.id, text=message.text, markdown=
            f'You don\t have tasks assigned, send me /START first')

        # If user's answer is not in range of the expected answers
        else:
            logger.info(f'{message.personId}:User\'s answer is not in range of '
                        f'the expected answers (1 to {check_answer})')
            api.messages.create(room.id, text=message.text, markdown=f'You should answer 1 to {check_answer}')

        return 'OK'

    elif "/repeat" in message.text.lower():
        logger.info(f'{message.personId}:FOUND "/repeat"')



        # check if that users exists
        if psql_obj.is_person_exists(message.personId):
            logger.info(f'{message.personId}:This is existing user')




            # check if that user already has task assigned
            has_task = Tasker.has_task(psql_obj,message.personId)

            logger.info(f'{message.personId}:That user has task? - {has_task}')

            if has_task:

                is_enough_flag = is_enough(psql_obj, message.personId)
                is_answered_flag = answer_received_for_current_task(psql_obj, message.personId)
                task_dict = {}  # dictionary structure for the task
                task_dict = get_current_task(psql_obj, message.personId, has_task)

                if is_answered_flag and is_enough_flag:
                    # If the user already completed all that tasks, we should not save answer from him

                    logger.info(f'{message.personId}:User has already answered for all the questions.'
                                f' Letting him know about that')
                    api.messages.create(room.id, text=message.text, markdown="You already answered all the tasks")

                elif task_dict['files']:
                    # exception handling in case can't find attachment

                    logger.info(f'{message.personId}:Picture path is not null, '
                                f'trying to add picture as attachment:{task_dict["files"]}')

                    try:
                        api.messages.create(room.id, text="Your current task:",
                                            markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']),
                                            files=task_dict['files'])
                    except ValueError:
                        logger.error(f'{message.personId}:Can\'t open file to attach:{task_dict["files"]}')

                        api.messages.create(room.id,
                                            markdown=f'<<Error: Can\'t open file to attach:{task_dict["files"]}>>')
                        api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                            markdown=prepare_markdown_quiz_task(task_dict,task_dict['task_number']))

                # If no attachment picture
                else:
                    logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                    api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
                                        markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

            else:

                logger.error(f'{message.personId}:We have that user in persons table, but don\'t have tasks assigned. '
                             'Notify him about that')

                api.messages.create(room.id, text="You don't have tasks assigned",
                                    markdown="You don't have tasks assigned")

        # user does not exist, create it and assign the task
        else:
            logger.info(f'{message.personId}:This is new user, no tasks assigned. Notify him about that')
            api.messages.create(room.id, text="You don't have tasks assigned", markdown="You don't have tasks assigned")

        return 'OK'

    elif "/help" in message.text.lower():
        logger.info(f'{message.personId}:FOUND "/help"')

        help_str = "**Commands supported:**\n" \
                   " * /start - start quiz's process\n" \
                   " * /repeat - repeat current question\n" \
                   " * [1-9] - send digit to chose an answer for the question\n"

        api.messages.create(room.id, text=help_str, markdown=help_str)

        return 'OK'

    else:
        logger.error(f'{message.personId}:Not valid option {message.text}, you can send only: /START or [digits]')

        api.messages.create(room.id, text="Not valid option, you can send only: /START or [digits]",
                            markdown="Not valid option, you can send only: /START or [digits]")
        return 'OK'

def sendWebexTeamsGET(url,bearer):
    request = urllib3.request(url,
                            headers={"Accept" : "application/json",
                                     "Content-Type":"application/json"})
    request.add_header("Authorization", "Bearer "+bearer)
    contents = urllib3.urlopen(request)

    return contents

def get_current_task(psql_obj,person_id, task_id: int) -> dict:

    dict_result = {
        'task':'',
        'task_id':'',
        'task_number':''
    }


    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)
    logger.info(f'{person_id}:All user tasks:{all_user_tasks}')

    task_number = len(all_user_tasks)

    task = Tasker.get_assigned_task_by_id(psql_obj, task_id)
    #dict_result = task

    dict_result['task'] = task['task']
    dict_result['task_id'] = task['id']
    dict_result['task_number'] = task_number

    return dict_result



def assign_new_task(psql_obj,person_id) -> dict:

    dict_result = {
        'task':'',
        'task_id':'',
        'task_number':'',
        'files' : [],
        'variants' : []
    }


    # incrementing task id in message to the customer

    #all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)
    #logger.info(f'{person_id}:All user tasks:{all_user_tasks}')

    #task_number = len(all_user_tasks) + 1

    task_number = 1
    task = Tasker.get_random_task(psql_obj,person_id)

    if task:
        #dict_result['task'] = task['task']
        #dict_result['task_id'] = task['id']
        #dict_result['task_number'] = task_number
        #dict_result['variants'] = task['variants']

        # Check whether we need to add attachment in message
        #if task["picture_path"]:
        #    # exception handling in case can't find attachment
        #    full_pict_path = os.path.join(config["pictures_folder"], task["picture_path"])
        #    logger.info(f'Picture path is not null, trying to add picture as attachment:{full_pict_path}')

        #    dict_result['files'] = [full_pict_path]
        # If no attachment picture
        #else:
        #    logger.info('Picture path is null, sending task without attachment')

        ##return dict_result

        """
        # Check whether we need to add attachment in message
        if task["picture_path"]:
            # exception handling in case can't find attachment
            full_pict_path = os.path.join(config["pictures_folder"],task["picture_path"])
            logger.info(f'Picture path is not null, trying to add picture as attachment:{full_pict_path}')

            try:
               api.messages.create(room.id, text=f"The {task_number} question for you:",
                                markdown=prepare_markdown_quiz_task(task,task_number),files=
                                [f'{full_pict_path}'])
            except ValueError:
                logger.error(f'Can\'t open file to attach:{task["picture_path"]}')

                api.messages.create(room.id,markdown=f'<<Error: Can\'t open file to attach:{full_pict_path}>>')
                api.messages.create(room.id, text=f"The {task_number} question for you:",
                                    markdown=prepare_markdown_quiz_task(task, task_number))

        # If no attachment picture
        else:
            logger.info('Picture path is null, sending task without attachment')
            api.messages.create(room.id, text=f"The {task_number} question for you:",
                                markdown=prepare_markdown_quiz_task(task,task_number))
        """


        # TODO: we are not randomizing tasks' answer list now
        if Tasker.assign_task(psql_obj,person_id, task["id"]):
            logger.info(f'{person_id}:Added task to the assigned_tasks table successfully')
        else:
            logger.info(f'{person_id}:Error in addition to assigned_tasks table')
            #return False
            # raise erorr if we could not add task to PSQL table, to catch this error at the upper level
            raise RuntimeError

    else:
        logger.info(f'{person_id}:User have answered all the question that we have')
        raise KeyError
        #api.messages.create(room.id, text="You have answered all the question that we have",
        #                    markdown="You have answered all the question that we have")

    return get_current_task(psql_obj,person_id,task["id"])
        #.assign_task(psql_obj,person_id, task["id"], task["answer"])

def save_user_answer(psql_obj,message) -> bool:

    # check if that user already has task assigned
    has_task = Tasker.has_task(psql_obj, message.personId)
    logger.debug(f'{message.personId}:Found current task id:{has_task}')

    task = Tasker.get_assigned_task_by_id(psql_obj, message.personId, has_task)

    if Tasker.save_user_answer(psql_obj, message.personId, task["id"], message.text):
        logger.info(f'{message.personId}:Successfully saved user answer')
        return True
    else:
        logger.info(f'{message.personId}:Error saving user answer')
        return False

def is_enough(psql_obj,person_id) -> bool:
    # Check whether we need to assign next question to the user

    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)
    logger.info(f'{person_id}:All user tasks:{all_user_tasks}')

    if len(all_user_tasks) >= config['tasks_num']:
        return True
    else:
        return False

def generate_report_dict(psql_obj,person_id) -> Dict:
    # Generate report for the user

    # creating dict for report
    dict_report = {'correct':[],'wrong':[]}

    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)
    logger.info(f'{person_id}:All user tasks:{all_user_tasks}')

    dict_report['correct'] = Tasker.get_correct_answers(psql_obj, person_id)
    dict_report['wrong'] = Tasker.get_wrong_answers(psql_obj, person_id)

    print(dict_report)

    return dict_report

def check_answer_in_range(psql_obj,person_id,answer_num:int) -> int:

    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)

    if len(all_user_tasks) > 0:

        # Get task id for the latest task

        task_id = all_user_tasks[0]["task_id"]
        logger.info(f'{person_id}:Latest task_id for the user {person_id}:{task_id}')


        task = Tasker.get_assigned_task_by_id(psql_obj, person_id, task_id)

        if answer_num in range(1,len(task["variants"])+1):
            return 0
        else:
            return len(task["variants"])

    else:
        # No assigned tasks found
        return -1

def answer_received_for_current_task(psql_obj,person_id) -> bool:
    # Check that we have received answer for the assigned task

    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)


    if len(all_user_tasks) > 0:
        # Get task id for the latest task

        if all_user_tasks[0]["user_answer"] == None:
            return False

        else:
            return True

    else:
        return False


def prepare_markdown_quiz_task(task: Dict, task_number:int) -> str:

    result_str = f'The #{task_number} task for you:<br/> {task["task"]}<br/>'

    result_str += f'Please send me your photo in attach.<br/> Additionally, you can send me' \
                  f' links to social networks, where you have shared this photos'

    return result_str




# Core bot functionality
# Your Webex Teams webhook should point to http://<serverip>:5000/events
#@flask_app.route('/events', methods=['GET', 'POST'])
@flask_app.route('/messages', methods=['GET', 'POST'])
def webex_teams_webhook_messages():
    logger.info(f'{message.personId}:TEST')
    return True

@flask_app.route('/', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/' URI."""

    if request.method == 'POST':
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