#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""Business intelligence for quiz bot to run on CLEUR lab 2293
"""

# Use future for Python v2 and v3 compatibility
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
from builtins import *
from typing import List

from flask import Flask, request
import requests
import yaml
import os
import logging
from typing import Dict, Any
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

from utils import setinitial
from utils import PSQL
from utils.tasker import Person, All_persons, Tasker


# Initializing logger
setinitial.setup_logging()
# create logger
logger = logging.getLogger(__name__)

config = {}  # create dictionary for config
try:
    config = setinitial.setup_config('config/config_quiz.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)


def attachment_not_supported(params: Dict) -> List[str]:
    """
    Function to notify user that attachments are not supported
    :return:
    """

    # List to put returned messages in
    result_list = []

    logger.error("Found attachment in user's input. Notifiying him that attachments are not supported")
    result_list.append('You can\'t send messages with attachments to me')

    return result_list


def cmd_start(params) -> List[str]:
    """
    **/start** - start the quiz and receive the tasks
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
        has_task = Tasker.has_task(psql_obj, message.personId)

        logger.info(f'{message.personId}:That user has task? - {has_task}')

        if has_task:

            is_enough_flag = is_enough(psql_obj, message.personId)
            is_answered_flag = answer_received_for_current_task(psql_obj, message.personId)
            task_dict = {}  # dictionary structure for the task
            task_dict = get_current_task(psql_obj, message.personId, has_task)

            if is_answered_flag and is_enough_flag:
                # If the user already completed all that tasks, we should not save answer from him

                logger.info(f'{message.personId}:User has already'
                            f' answered for all the questions. Letting him know about that')
                result_list.append("You already answered all the tasks")

            elif task_dict['files']:
                result_list.append("You already have the task. Please answer it first")

                # exception handling in case can't find attachment

                logger.info(f'{message.personId}:Picture path is not null,'
                            f' trying to add picture as attachment:{task_dict["files"]}')

                result_list.append([prepare_markdown_quiz_task(task_dict, task_dict['task_number']),
                                    task_dict['files']])

            # If no attachment picture
            else:
                result_list.append("You already have the task. Please answer it first")

                logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

        else:

            if has_tech(psql_obj,message.personId):
                logger.error(f'{message.personId}:We have that user'
                             f' in persons table, but don\'t have assigned tasks for him')
                logger.error(f'{message.personId}:Assigning task for him')

                task_dict = {}  # dictionary structure for the task
                try:
                    tech = Tasker.get_person(psql_obj, message.personId)['tech']
                    task_dict = assign_new_task(psql_obj, message.personId,tech)
                except RuntimeError:
                    # Error in addition to assigned_tasks table
                    logger.fatal('Error in addition to assigned_tasks table')
                    return result_list
                except KeyError:
                    # User have answered all the question that we have

                    result_list.append("You have answered all the question that we have")
                    return result_list

                if task_dict['files']:
                    # exception handling in case can't find attachment

                    logger.info(f'{message.personId}:Picture path is not null,'
                                f' trying to add picture as attachment:{task_dict["files"]}')

                    result_list.append([prepare_markdown_quiz_task(task_dict, task_dict['task_number'])
                                       ,task_dict['files']])

                # If no attachment picture
                else:
                    logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                    result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))
            else:
                result_list.extend(get_all_tech(params))

    # user does not exist, create it and assign the task
    else:
        logger.info(f'{message.personId}:This is new user')
        result_list.append("You are **new** user")

        # Creating new user
        if psql_obj.add_person(message.personId, person_name, person_surname, message.personEmail):
            logger.info(f'{message.personId}:User {message.personId} created user successfully')
            # assign_new_task(api, psql_obj, room, message)

            # Ask user to choose tech
            result_list.extend(get_all_tech(params))

        else:
            logger.error(f'{message.personId}:User {message.personId} creation failed')

    return result_list

def create_first_task(params):

    person = params['person']
    message = params['message']
    psql_obj = params['psql_obj']

    person_name = person.firstName
    person_surname = person.lastName

    # List to put returned messages in
    result_list = []

    task_dict = {}  # dictionary structure for the task
    try:
        tech = Tasker.get_person(psql_obj, message.personId)['tech']
        task_dict = assign_new_task(psql_obj, message.personId,tech)
    except RuntimeError:
        # Error in addition to assigned_tasks table
        logger.fatal('Error in addition to assigned_tasks table')
        return result_list
    except KeyError:
        # User have answered all the question that we have
        result_list.append("You have answered all the question that we have")
        return result_list

    if task_dict['files']:
        # exception handling in case can't find attachment

        logger.info(f'{message.personId}:Picture path is not null,'
                    f' trying to add picture as attachment:{task_dict["files"]}')

        result_list.append([prepare_markdown_quiz_task(task_dict, task_dict['task_number']),
                            task_dict['files']])

    # If no attachment picture
    else:
        logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
        result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

    return result_list

def process_input_digit(params) -> List[str]:
    """
    Function to process incoming digit (answer) for the task
    """

    person = params['person']
    message = params['message']
    psql_obj = params['psql_obj']

    person_name = person.firstName
    person_surname = person.lastName

    # List to put returned messages in
    result_list = []

    logger.info(f'{message.personId}:FOUND "[digit]" in message:{message.text}')

    # If answer in range of the expected answers
    check_answer = check_answer_in_range(psql_obj, message.personId, int(message.text))

    is_enough_flag = is_enough(psql_obj, message.personId)
    is_answered_flag = answer_received_for_current_task(psql_obj, message.personId)

    if is_answered_flag and is_enough_flag:
        # If the user already completed all that tasks, we should not save answer from him

        logger.info(f'{message.personId}:User has already answered for'
                    f' all the questions. Letting him know about that')
        result_list.append("You already answered all the tasks")

    # If user's answer is in expected range
    elif check_answer == 0:
        save_user_answer(psql_obj, message)

        result_list.append("Thank you, your answer was accepted")

        # Check that user has answered all questions and we need to prepare report for him
        if is_enough_flag:
            report_dict = {}

            result_list.append("You have completed the quiz. Preparing score for you")
            report_dict = generate_report_dict(psql_obj, message.personId)
            result_list.append("**Answered correctly:**")

            for correct_answer in report_dict['correct']:
                task = Tasker.get_assigned_task_by_id(psql_obj, message.personId, correct_answer["task_id"])

                result_list.append(f'- {task["task"][0:100]}<...>')

            result_list.append("**Answered incorrectly [your_answer -> right answer]:**")

            for wrong_answer in report_dict['wrong']:
                task = Tasker.get_assigned_task_by_id(psql_obj, message.personId, wrong_answer["task_id"])
                text = f'- {task["task"]} [{wrong_answer["user_answer"]}->{wrong_answer["loc_answer"]}]'

                if task['explain'] is not None:
                    # Task has explanation attached. Add it to the wrong answers
                    logger.info('Task has explanation attached. Add it to the wrong answers')
                    text += f'<br/>**Explanation:**<br/>{task["explain"]}'

                result_list.append(text)

        else:
            task_dict = {} # dictionary structure for the task
            try:
                tech = Tasker.get_person(psql_obj, message.personId)['tech']
                task_dict = assign_new_task(psql_obj, message.personId,tech)
            except RuntimeError:
                #Error in addition to assigned_tasks table
                logger.error("Error in addition to assigned_tasks table")
                return result_list
            except KeyError:
                #User have answered all the question that we have

                result_list.append("You have answered all the question that we have")
                return result_list

            if task_dict['files']:
                # exception handling in case can't find attachment

                logger.info(f'{message.personId}:Picture path is not null, '
                            f'trying to add picture as attachment:{task_dict["files"]}')

                result_list.append([prepare_markdown_quiz_task(task_dict, task_dict['task_number']),
                                    task_dict['files']])

            # If no attachment picture
            else:
                logger.info(f'{message.personId}:Picture path is null, sending task without attachment')
                result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

    # If user doesn't have tasks assigned
    elif check_answer == -1:
        logger.info(f'{message.personId}:User does not have tasks assigned')
        result_list.append(f'You don\'t have tasks assigned, send me /start first')

    # If user's answer is not in range of the expected answers
    else:
        logger.info(f'{message.personId}:User\'s answer is not in range of '
                    f'the expected answers (1 to {check_answer})')
        result_list.append(f'You should answer 1 to {check_answer}')

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
                result_list.append("You already answered all the tasks")

            elif task_dict['files']:
                # exception handling in case can't find attachment

                logger.info(f'{message.personId}:Picture path is not null, '
                            f'trying to add picture as attachment:{task_dict["files"]}')

                result_list.append([prepare_markdown_quiz_task(task_dict, task_dict['task_number']),
                                    task_dict['files']])

            # If no attachment picture
            else:
                logger.info(f'{message.personId}:Picture path is null, sending task without attachment')

                result_list.append(prepare_markdown_quiz_task(task_dict, task_dict['task_number']))

        else:

            logger.error(f'{message.personId}:We have that user in persons table, but don\'t have tasks assigned. '
                         'Notify him about that')

            result_list.append("You don't have tasks assigned")

    # user does not exist, create it and assign the task
    else:
        logger.info(f'{message.personId}:This is new user, no tasks assigned. Notify him about that')
        result_list.append("You don't have tasks assigned")

    return result_list


def cmd_help(params) -> List[str]:
    """**/help** - print list of supported commands"""
    results = []
    for obj in globals():
        if 'cmd_' in obj and obj is not 'cmd_default':
            results.append(globals()[obj].__doc__)
    results.append("[1-9] - send digit to chose an answer for the question")
    return results


def cmd_default(params) -> List[str]:
    """
    Function default to process all unsupported messages received
    """

    person = params['person']
    message = params['message']
    psql_obj = params['psql_obj']

    person_name = person.firstName
    person_surname = person.lastName

    # List to put returned messages in
    result_list = []

    logger.error(f'{message.personId}:Not valid option {message.text}, you can send only: /START or [digits]')

    result_list.append("Not valid option, you can send only. List of supported commands:")
    result_list.extend(cmd_help(params))

    return result_list

def has_tech(psql_obj,person_id) -> bool:
    if Tasker.get_person(psql_obj,person_id)['tech'] is not None:
        return True
    else:
        return False

def choose_tech(params) -> List[str]:
    psql_obj = params['psql_obj']
    message = params['message']

    tech_id = int(params['message'].text)

    result_list = []

    tech_list = Tasker.get_tech_list(psql_obj)

    if tech_id > len(tech_list):
        result_list.append(f'Choose option from 1 to {len(tech_list)}')
        result_list.extend(get_all_tech(params))
        return result_list
    else:
        Tasker.save_tech(psql_obj, message.personId, tech_list[tech_id-1][0])
        tech_list.append(f'Thank you, technology {tech_list[tech_id-1][0]} saved')
        result_list.append(f'*Chosen technology:* **{tech_list[tech_id-1][0]}**')

        result_list.extend(create_first_task(params))

        return result_list


def get_all_tech(params) -> List[str]:
    psql_obj = params['psql_obj']

    result_list = []

    i = 0
    str_tech = 'Enter # of technology for which you want to receive tasks:<br/>'
    for tech in Tasker.get_tech_list(psql_obj):
        i += 1
        str_tech += f'{i}. {tech[0]}<br/>'

    result_list.append(str_tech)
    return result_list


def get_current_task(psql_obj,person_id, task_id: int) -> dict:

    dict_result = {
        'task':'',
        'task_id':'',
        'task_number':'',
        'files' : [],
        'variants' : []
    }

    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)
    logger.info(f'{person_id}:All user tasks:{all_user_tasks}')

    task_number = len(all_user_tasks)

    task = Tasker.get_assigned_task_by_id(psql_obj, person_id, task_id)

    dict_result['task'] = task['task']
    dict_result['task_id'] = task['id']
    dict_result['task_number'] = task_number
    dict_result['variants'] = task['variants']

    # Check whether we need to add attachment in message
    if task["picture_path"]:
        # exception handling in case can't find attachment
        full_pict_path = os.path.join(config["pictures_folder"], task["picture_path"])
        logger.info(f'{person_id}:Picture path is not null,'
                    f' trying to add picture as attachment:{full_pict_path}')

        dict_result['files'] = [full_pict_path]
    # If no attachment picture
    else:
        logger.info(f'{person_id}:Picture path is null, sending task without attachment')

    return dict_result


def assign_new_task(psql_obj,person_id,tech) -> dict:

    dict_result = {
        'task':'',
        'task_id':'',
        'task_number':'',
        'files' : [],
        'variants' : []
    }

    # incrementing task id in message to the customer

    all_user_tasks = Tasker.get_assigned_tasks_by_person(psql_obj, person_id)
    logger.info(f'{person_id}:All user tasks:{all_user_tasks}')

    task_number = len(all_user_tasks) + 1

    task = Tasker.get_random_task(psql_obj,person_id,tech)

    if task:
        # TODO: we are not randomizing tasks' answer list now
        if Tasker.assign_task(psql_obj,person_id, task["id"], task["answer"]):
            logger.info(f'{person_id}:Added task to the assigned_tasks table successfully')
        else:
            logger.info(f'{person_id}:Error in addition to assigned_tasks table')

            # raise erorr if we could not add task to PSQL table, to catch this error at the upper level
            raise RuntimeError

    else:
        logger.info(f'{person_id}:User have answered all the question that we have')
        raise KeyError

    return get_current_task(psql_obj,person_id,task["id"])


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

        if all_user_tasks[0]["user_answer"] is None:
            return False

        else:
            return True

    else:
        return False


def prepare_markdown_quiz_task(task: Dict, task_number:int) -> str:

    result_str = f'The #{task_number} question for you:<br/>'
    result_str += f'----------------------------------------------------<br/>'
    result_str += f'{task["task"]}<br/>'
    result_str += f'----------------------------------------------------<br/>'

    i = 1 # options' counter

    for option in task["variants"]:
        result_str += f'{i}. {option}<br/>'
        i += 1

    result_str += f'----------------------------------------------------<br/>'
    result_str += f'Choose your answer (1 to {i-1}):'

    return result_str
