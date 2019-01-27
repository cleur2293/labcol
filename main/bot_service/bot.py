import logging
import os,sys,inspect
from webexteamssdk import WebexTeamsAPI, Webhook
from bi_template import *

logger = logging.getLogger(__name__) # Creating logger for logging across this module

# Create the Webex Teams API connection object
#api = WebexTeamsAPI(access_token='MTVmMGE3Y2YtYzdiNi00ZGI2LTgzYjUtMjg2ZmNhMzEwZTM1MmZiNWQyOGItZWEy_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f')

# To be able to load modules from parent directory
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)


# Core bot functionality
def process_message(api: WebexTeamsAPI,json_data):
    # Create a Webhook object from the JSON data
    webhook_obj = Webhook(json_data)
    # Get the room details
    room = api.rooms.get(webhook_obj.data.roomId)
    # Get the message details
    message = api.messages.get(webhook_obj.data.id)
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
        params = dict()
        params['person'] = person
        params['room'] = room
        params['message'] = message
        results = process_command(params)
        for result in results:
            # Post the response to the room where the request was received
            api.messages.create(room.id, markdown=result)
        return 'OK'


def process_command(params):
    command = params['message'].text.lower().split()[0]
    if command[0] == '/' and f'cmd_{command[1:]}' in globals():
        return globals()[f'cmd_{command[1:]}'](params)
    elif 'cmd_default' in globals():
        return globals()['cmd_default'](params)
    else:
        return ['Invalid command. Please use /help for list of commands.']
