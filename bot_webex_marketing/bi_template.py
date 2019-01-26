#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""Business intelligence for marketing bot to run on CLEUR lab 2293
"""


import requests
import yaml
import os
import re
import logging
from typing import Dict, Any, List
import urllib3
import certifi
from socket import error as socket_error
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

from utils import setinitial
from utils import PSQL_marketing
from utils.tasker_marketing import Tasker
from utils import emailsend2
from utils import webhook


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


def process_received_photo(params) -> List[str]:
        """
        Function to process photos received from the user
        :param params:
        :return:
        """

        person = params['person']
        message = params['message']
        psql_obj = params['psql_obj']

        person_name = person.firstName
        person_surname = person.lastName

        # List to put returned messages in
        result_list = []


        logger.error(f'Found attachment in user\'s input.')
        logger.error(f'message.files={message.files}')

        # check that user has task assigned
        task_id = Tasker.has_task(psql_obj, message.personId)
        if task_id:

            for file_url in message.files:
                logger.info(f'Accessing:{file_url}')
                response = sendWebexTeamsGET(file_url,config['bot_access_token'])
                content_disp = response.headers.get('Content-Disposition', None)
                logger.info(f'content_disp:{content_disp}')
                if content_disp is not None:
                    filename = content_disp.split("filename=")[1]
                    filename = filename.replace('"', '')
                    filename = marketing_pict_path(message.personId,
                                                   person_name,
                                                   person_surname,
                                                   filename,task_id)

                    logger.info(f'result filename:{filename}')
                    with open(filename, 'wb') as out:
                            data = response.data
                            if not data:
                                logger.error('Can\'t find data in response')
                            else:
                                out.write(data)
                else:
                    logger.info('Cannot save file- no Content-Disposition header received.')

            #api.messages.create(room.id, text="Your attachment received successfully")
            result_list.append("Your attachment received successfully")

            # Insert into received content table and receive epoch_id
            epoch_id = psql_obj.add_received_photos(task_id,message.personId,filename)

            if epoch_id != -1:
                logger.info(f'{message.personId}:Successfully updated assigned_tasks table epoch:{epoch_id}'
                            f' with new received picture')

                # Prepare and build email to send for approval
                #person_name = api.people.get(message.personId).firstName
                #person_surname = api.people.get(message.personId).lastName

                email_text = build_unresolved_tasks_table(psql_obj, message.personId,
                                                          person_name,
                                                          person_surname,
                                                          message.personEmail, epoch_id, is_links=False)
                # Send notification to the administrator
                try:
                    logger.info('Sending email with attached photo for approval')
                    emailsend2.action(subject=f'WebexBot:Photo received uid={task_id}.{epoch_id}'
                                              f' person {person_name}:{person_surname}',
                                      email_list=[
                                          email_text],
                                      email_test=False,
                                      attached_photo=filename
                                      )
                except socket_error:
                    logger.error("Unable to connect to SMTP server")
                except Exception as exc:
                    logger.error("Send mail error:" + str(exc))

            else:
                logger.error(f'{message.personId}:Error during update of assigned_tasks '
                            f'table with new received picture')
        else:
            logger.error(f'{message.personId}:Does not have tasks assigned')
            #api.messages.create(room.id, text=f'You don\'t have tasks assigned, run /start first',
            #                        markdown=f'You don\'t have tasks assigned, run /start first')
            result_list.append("You don\'t have tasks assigned, run /start first")

        return result_list


def cmd_start(params) -> List[str]:
    """
    **/start** - register yourself in marketing campaign and receive the start receive the tasks
    """

    person = params['person']
    message = params['message']
    psql_obj = params['psql_obj']

    person_name = person.firstName
    person_surname = person.lastName

    # List to put returned messages in
    result_list = []


    logger.info(f'{message.personId}:FOUND "/start"')


    # check if that users exists
    if psql_obj.is_person_exists(message.personId):
        logger.info(f'{message.personId}:This is existing user')

        # check if that user already has task assigned
        has_task = Tasker.has_task(psql_obj,message.personId)

        logger.info(f'{message.personId}:That user has task? - {has_task}')

        if has_task != -1:

            task_dict = {}  # dictionary structure for the task
            task_dict = get_current_task(psql_obj, message.personId, has_task)

            #api.messages.create(room.id, text="You already have the task. Please answer it first",
            #                markdown="You already have the task. Please answer it first")
            result_list.append('You already have the task. Please answer it first')

            logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
            #api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
            #                    markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))
            result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

        else:

            logger.error(f'{message.personId}:We have that user'
                         f' in persons table, but don\'t have assigned tasks for him')
            logger.error(f'{message.personId}:Assigning task for him')


            task_dict = {} # dictionary structure for the task
            try:
                task_dict = assign_new_task(psql_obj, message.personId)
            except RuntimeError:
                #Error in addition to assigned_tasks table
                logger.error('Error in addition to assigned_tasks table')
                return result_list
            except KeyError:
                #User have answered all the question that we have
                #api.messages.create(room.id, text="You have answered all the question that we have",
                #                markdown="You have answered all the question that we have")
                result_list.append("You have answered all the question that we have")
                return result_list

            #api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
            #                    markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))
            result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))


    # user does not exist, create it and assign the task
    else:
        logger.info(f'{message.personId}:This is new user')
        #api.messages.create(room.id, text="You are new user", markdown="You are **new** user")
        result_list.append("You are new user")

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
                # Error in addition to assigned_tasks table
                logger.error('Error in addition to assigned_tasks table')
                return result_list
            except KeyError:
                # User have answered all the question that we have
                # api.messages.create(room.id, text="You have answered all the question that we have",
                #                markdown="You have answered all the question that we have")
                result_list.append("You have answered all the question that we have")
                return result_list

            logger.info(f'{message.personId}Sending task')
            #api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
            #                        markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))
            result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

        else:
            logger.error(f'{message.personId}:User {message.personId} creation failed')


    return result_list


def cmd_repeat(params) -> List[str]:
    """
    **/repeat** - get the text of your current task
    """

    person = params['person']
    message = params['message']
    psql_obj = params['psql_obj']

    person_name = person.firstName
    person_surname = person.lastName

    # List to put returned messages in
    result_list = []

    logger.info(f'{message.personId}:FOUND "/repeat"')

    # Check if that user exists
    if psql_obj.is_person_exists(message.personId):
        logger.info(f'{message.personId}:This is existing user')

        # check if that user already has task assigned
        has_task = Tasker.has_task(psql_obj, message.personId)

        logger.info(f'{message.personId}:That user has task? - {has_task}')

        if has_task != -1:

            task_dict = {}  # dictionary structure for the task
            task_dict = get_current_task(psql_obj, message.personId, has_task)

            #api.messages.create(room.id, text="You already have the task. Please answer it first",
            #                    markdown="You already have the task. Please answer it first")
            result_list.append("Repeating your current task.")

            logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
            #api.messages.create(room.id, text=f"The {task_dict['task_number']} question for you:",
            #                    markdown=prepare_markdown_quiz_task(task_dict, task_dict['task_number']))
            result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

        else:

            logger.error(f'{message.personId}:We have that user'
                         f' in persons table, but don\'t have assigned tasks for him')
            logger.error(f'{message.personId}:Assigning task for him')

            #api.messages.create(room.id, text=f"You don\'t have tasks assigned, please run /start first",
            #                    markdown=f"You don\'t have tasks assigned, please run */start* first")
            result_list.append("You don\'t have tasks assigned, please run */start* first")

    # user does not exist, create it and assign the task
    else:
        logger.info(f'{message.personId}:This is new user, no tasks assigned. Notify him about that')
        #api.messages.create(room.id, text=f"You don\'t have tasks assigned, please run /start first",
        #                    markdown=f"You don\'t have tasks assigned, please run */start* first")
        result_list.append("You don\'t have tasks assigned, please run */start* first")

    return result_list


def cmd_help(params):
    """**/help** - print list of supported commands"""
    results = []
    for obj in globals():
        if 'cmd_' in obj and obj is not 'cmd_default':
            results.append(globals()[obj].__doc__)
    return results

def process_received_links(params) -> List[str]:
    """
    Function to process links received from the user
    :param params:
    :return:
    """

    person = params['person']
    message = params['message']
    psql_obj = params['psql_obj']

    person_name = person.firstName
    person_surname = person.lastName

    # List to put returned messages in
    result_list = []

    logger.info(f'{message.personId}:Probably user send us link to social network, checking the links')

    task_id = Tasker.has_task(psql_obj, message.personId)
    if task_id:

        if is_allowed_link(message.text.lower()):
            logger.info(f'{message.personId}:Found social media in provided link')
            #api.messages.create(room.id, text=f'Valid social network link: {message.text}',
            #                    markdown=f'Valid social network link: {message.text}')
            result_list.append(f'Valid social network link: {message.text}')

            # Insert into received content table and receive epoch_id
            epoch_id = psql_obj.add_received_links(task_id, message.personId, message.text.lower())

            if epoch_id != -1:
                logger.info(f'{message.personId}:Successfully updated assigned_tasks '
                            f'table with new received link')
                #api.messages.create(room.id, text=f'Valid link, saved: {message.text}',
                #                    markdown=f'Valid link, saved: {message.text}')
                result_list.append(f'Valid link, saved: {message.text}')

                # Prepare and build email to send for approval
                email_text = build_unresolved_tasks_table(psql_obj, message.personId,
                                                          person_name,
                                                          person_surname,
                                                          message.personEmail, epoch_id, is_links=True)
                # Send notification to the administrator
                try:
                    emailsend2.action(subject=f'WebexBot:Link received uid={task_id}.{epoch_id}'
                                              f' person {person_name}:{person_surname}',
                                      email_list=[
                                          email_text],
                                      email_test=False)
                except socket_error:
                    logger.error("Unable to connect to SMTP server")
                except Exception as exc:
                    logger.error("Send mail error:" + str(exc))

            else:
                logger.error(f'{message.personId}:Error during update of assigned_tasks '
                             f'table with new received link')

        else:
            logger.error(f'{message.personId}:Not valid social network link: {message.text}')
            #api.messages.create(room.id, text=f'Not valid social network link: {message.text}',
            #                    markdown=f'Not valid social network link: {message.text}')
            result_list.append(f'Not valid social network link: {message.text}')


    else:
        logger.error(f'{message.personId}:Does not have tasks assigned')
        #api.messages.create(room.id, text=f'You don\'t have tasks assigned, run /start first',
        #                    markdown=f'You don\'t have tasks assigned, run /start first')
        result_list.append('You don\'t have tasks assigned, run /start first')

    return result_list


def is_allowed_link(link:str) -> bool:

    logger.info(f'Patterns for social networks:{config["social_media"]}')
    for url in config['social_media']:
        pattern = re.compile(f'{url}')
        if pattern.match(link.lower()):
            return True
    return False


def marketing_pict_path(person_id:str,firstName:str,lastName:str, filename:str, task_id: int) -> str:

    try:
        folder = config['rec_pictures_folder']
    except KeyError:
        logger.error('{person_id}:Can\'t find \'rec_pictures_folder\' in config file.')
        folder = 'rec_pictures_folder'

    logger.info(f'Using received_pictures folder:{folder}')

    base_name = os.path.join(folder,f'{lastName.lower()}_{firstName.lower()}_{person_id[0:4]}',str(task_id))
    if not os.path.isdir(base_name):
        logger.info(f'Directory:{base_name} does not exist. Creating it')
        os.makedirs(base_name, exist_ok=True)

    return os.path.join(base_name,filename.lower())


def sendWebexTeamsGET(url,bearer):
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                               ca_certs=certifi.where())
    request = http.request('GET',url,
                            headers={"Accept" : "application/json",
                                     "Content-Type":"application/json",
                                     "Authorization": "Bearer " + bearer})

    return request

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

    dict_result['task'] = task['task']
    dict_result['task_id'] = task['id']
    dict_result['task_number'] = task_number

    return dict_result


def assign_new_task(psql_obj,person_id) -> dict:

    task = Tasker.get_random_task(psql_obj,person_id)

    if task:
        if Tasker.assign_task(psql_obj,person_id, task["id"]):
            logger.info(f'{person_id}:Added task to the assigned_tasks table successfully')
        else:
            logger.info(f'{person_id}:Error in addition to assigned_tasks table')

            # raise erorr if we could not add task to PSQL table, to catch this error at the upper level
            raise RuntimeError

    else:
        logger.info(f'{person_id}:User have answered all the question that we have')
        raise KeyError

    return get_current_task(psql_obj,person_id,task["id"])


def is_enough(psql_obj) -> bool:
    # Check whether we need to assign next question to the user

    task_runs = Tasker.get_task_runs(psql_obj)
    logger.info(f'Task runs:{task_runs["count"]}')

    if task_runs['count'] >= config['marketing_runs']:
        return True
    else:
        return False


def prepare_markdown_quiz_task(task: Dict, task_number:int) -> str:

    result_str = f'The #{task_number} task for you:<br/> {task["task"]}<br/>'

    result_str += f'Please send me photo with you for that task in attach.<br/> Additionally, you can send me' \
                  f' links to social networks, where you have shared this photos'

    return result_str


def build_unresolved_tasks_table(psql_obj,person_id: str,person_name:str, person_surname:str, person_email:str,
                                epoch,
                                 is_links = False) -> str:
    table = []
    table_top = '<table><tbody>'
    table_bottom = '</tbody></table>'

    # check if that user already has task assigned
    has_task = Tasker.has_task(psql_obj, person_id)

    logger.info(f'{person_id}:Current task_id - {has_task}')

    task = get_current_task(psql_obj, person_id, has_task)

    #tasks = Tasker.get_assigned_tasks_by_person(psql_obj,person_id)

    table_header = f'<b>Current task for the user:</b> {person_name} {person_surname} ({person_email}):'
    table.append(table_header)
    table.append(table_top)
    task_text = '<tr><td>{}</td>'.format(Tasker.get_assigned_task_by_id(psql_obj, task['task_id'])['task'])
    table.append(task_text)

    if is_links:
        #If we received link to social network
        table_form = build_for_links_received(psql_obj, person_id, task['task_id'],epoch)
    else:
        #If we received picture
        table_form = build_for_picture_received(person_id, task['task_id'],epoch)

    table.append(table_form)
    table.append(table_bottom)
    return '\n'.join(table)


def build_for_picture_received(person_id:str, task_id:int, epoch: int) -> str:
    task_form = '<tr><b>Check the picture below and make a decision:</b></tr>'

    task_form += '<tr>' \
                 '<td width=20% align="center" valign="middle">' \
                 '<a href="http:/{}:5000/approve_content?person_id={}&task_id={}&epoch={}&approved={}">Approve</a>' \
                 '</td>' \
                 '<td width=20% align="center" valign="middle">' \
                 '<a href="http:/{}:5000/approve_content?person_id={}&task_id={}&epoch={}&approved={}">Reject</a>' \
                 '</td>' \
                 '</tr>'.format('127.0.0.1',
                                person_id,
                                task_id,
                                epoch,
                                'True',
                                '127.0.0.1',
                                person_id,
                                task_id,
                                epoch,
                                'False')

    return task_form


def build_for_links_received(psql_obj,person_id:str, task_id:int, epoch: int) -> str:

    logger.info('is_links found')

    # If we receive the link from the user, print all received links for that task

    all_received_links = Tasker.get_received_links_by_person(psql_obj,person_id,task_id)

    # Print currently received link
    task_form = '<tr><b>Current link to social network:</b></tr>'

    #link = all_received_links[len(all_received_links)-1]
    link = Tasker.get_received_link_by_person_epoch(psql_obj,person_id,task_id,epoch)
    task_form += '<tr>' \
                '<td>{}</td>' \
                '<td>{}</td>' \
                '<td width=20% align="center" valign="middle">' \
                '<a href="http:/{}:5000/approve_content?person_id={}&task_id={}&epoch={}&approved={}">Approve</a>' \
                '</td>' \
                '<td width=20% align="center" valign="middle">' \
                '<a href="http:/{}:5000/approve_content?person_id={}&task_id={}&epoch={}&approved={}">Reject</a>' \
                '</td>'\
                '</tr>'.format(link['received_links'],
                               link['epoch'],
                               '127.0.0.1',
                               person_id,
                               task_id,
                               epoch,
                               'True',
                               '127.0.0.1',
                               person_id,
                               task_id,
                               epoch,
                               'False')

    task_form += '<tr>Another links received by user, for this task:</tr>'
    task_form += '<tr><td><b>uid</b></td><td><b>link</b></td><td><b>status</b></td></tr>'
    for link in all_received_links:
        if link['epoch'] != epoch:
            task_form = task_form + '<tr><td>{}.{}</td><td>{}</td><td>{}</td></tr>'.format(link['task_id'], link['epoch'],
                                                                  link['received_links'], link['status'])
        else:
            logger.info(f'Skipping epoch={epoch}')

    return task_form


def build_unresolved_task_form(psql_obj,person_id:str, task_id:int) -> str:

    task_text = Tasker.get_assigned_task_by_id(psql_obj,task_id)['task']
    task_form = '<tr> \
                <td>{}</td> \
                <td width=20% align="center" valign="middle"> \
                <a href="http:/{}:5000/update_task?person_id={}&task_id={}&approved={}">Approve</a> \
                </td> \
                </tr>'.\
        format(task_text[:50], '127.0.0.1', person_id, task_id, 'True')
    return task_form
