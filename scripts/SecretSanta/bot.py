#!/usr/bin/env python
#  -*- coding: utf-8 -*-

# Use future for Python v2 and v3 compatibility
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import builtins

from flask import Flask, request
from webexteamssdk import WebexTeamsAPI, Webhook
import json
import time
from dates import *

# If user is registered
def is_registered_user(person_id):
    try:
        with open("users.json", "r") as read_file:
            json_users = json.load(read_file)
    except FileNotFoundError:
        json_users = []
    if any(json_user['id'] == person_id for json_user in json_users):
        return True
    return False

# /Start
def register_user(person, room_id):
    if time.time() < LAST_DAY_TO_REGISTER:
        return 'Registration is closed now'
    try:
        with open("users.json", "r") as read_file:
            json_users = json.load(read_file)
    except FileNotFoundError:
        json_users = []
    if any(json_user['id'] == person.id for json_user in json_users):
        return 'You are registered already'
    else:
        json_users.append({'id': person.id, 'emails': person.emails, 'displayName': person.displayName, 'firstName': person.firstName, 'lastname': person.lastName, 'room': room_id, 'pair': '', 'gift': '', 'bought': False, 'placed': False})
        with open("users.json", "w") as write_file:
            json.dump(json_users, write_file)
        return 'You are registered now. I will send you additional information at a later date'

# /Ask
def ask_gift(person_id):
    with open("users.json", "r") as read_file:
        json_users = json.load(read_file)
    for index, user in enumerate(json_users):
        if user['id'] == 'person_id':
            break
        else:
            index = -1
    for pair_index, user in enumerate(json_users):
        if user['id'] == json_users[index]['pair']:
            break
        else:
            pair_index = -1
    gift = json_users[pair_index]['gift']
    if gift:
        return 'Your pair wants to get **'+gift+'** on Christmas'
    else:
        api.messages.create(json_users[pair_index]['room'], markdown='Please let me know what do you want to get on Christmas by sending **/want _your gift_** message to me')
        return 'I asked your pair what does he/she want to get on Christmas. I will let you know about it once I get response'

# /Want
def want_gift(person_id, gift_name):
    with open("users.json", "r") as read_file:
        json_users = json.load(read_file)
    for index, user in enumerate(json_users):
        if user['id'] == 'person_id':
            break
        else:
            index = -1
    for pair_index, user in enumerate(json_users):
        if user['id'] == json_users[index]['pair']:
            break
        else:
            pair_index = -1
    if not json_users[pair_index]['bought']:
        json_users[index]['gift'] = gift_name
        with open("users.json", "w") as write_file:
           json.dump(json_users, write_file)
        api.messages.create(json_users[pair_index]['room'], markdown='Your pair wants to get **'+gift_name+'** on Christmas')
        return 'I will inform your pair about that'
    else:
        return 'Your pair has bought you a gift already'


# /Bought
def bought_gift(person_id):
    with open("users.json", "r") as read_file:
        json_users = json.load(read_file)
    for index, user in enumerate(json_users):
        if user['id'] == 'person_id':
            break
        else:
            index = -1
    json_users[index]['bought'] = True
    with open("users.json", "w") as write_file:
        json.dump(json_users, write_file)
    return 'Great! Please do not forget to place the gift under a Christmas tree. Once you placed a gift please send me a confirmation by **/placed** message'

# /Placed
def placed_gift(person_id):
    with open("users.json", "r") as read_file:
        json_users = json.load(read_file)
    for index, user in enumerate(json_users):
        if user['id'] == 'person_id':
            break
        else:
            index = -1
    if json_users[index]['bought']:
        json_users[index]['placed'] = True
        with open("users.json", "w") as write_file:
            json.dump(json_users, write_file)
        return 'Well done! I hope you pair will be happy on Christmas'
    else:
        return 'You need to buy a gift. Once you have it please send me command **/bought** for confirmation'


# Initialize the environment
# Create the web application instance
flask_app = Flask(__name__)
# Create the Webex Teams API connection object
api = WebexTeamsAPI(access_token='MGZjOGFkNGUtNmQ5OC00Y2UzLWE0MjktNjAyYmNhMzBmOTQwNThhZGU3NjctNWYy')

# Core bot functionality
# Your Webex Teams webhook should point to http://<serverip>:5000/events
@flask_app.route('/events', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/events' URI."""
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
                   <blockquote>Santa Quest</blockquote>
                   </body>
                   </html>
                """)
    elif request.method == 'POST':
        """Respond to inbound webhook JSON HTTP POST from Webex Teams."""

        # Get the POST data sent from Webex Teams
        json_data = request.json
        print("\n")
        print("WEBHOOK POST RECEIVED:")
        print(json_data)
        print("\n")

        # Create a Webhook object from the JSON data
        webhook_obj = Webhook(json_data)
        # Get the room details
        room = api.rooms.get(webhook_obj.data.roomId)
        # Get the message details
        message = api.messages.get(webhook_obj.data.id)
        # Get the sender's details
        person = api.people.get(message.personId)

        print("NEW MESSAGE IN ROOM '{}'".format(room.title))
        print("FROM '{}'".format(person.displayName))
        print("MESSAGE '{}'\n".format(message.text))

        # This is a VERY IMPORTANT loop prevention control step.
        # If you respond to all messages...  You will respond to the messages
        # that the bot posts and thereby create a loop condition.
        me = api.people.me()
        if message.personId == me.id:
            # Message was sent by me (bot); do not respond.
            return 'OK'

        else:
            # Message was sent by someone else; parse message and respond.
            if not is_registered_user(person.id):
                api.messages.create(room.id, markdown='You are not registered. Please send **/start** message to me')
            elif "/start" in message.text and time.time() <= LAST_DAY_TO_REGISTER:
                print("FOUND '/start'")
                # Get a response
                user_registration_response = register_user(person, room.id)
                print("SENDING RESPONSE '{}'".format(user_registration_response))
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown=user_registration_response)
            elif "/ask" in message.text and time.time() > LAST_DAY_TO_REGISTER:
                print("FOUND '/ask'")
                # Get a response
                ask_gift_response = ask_gift(person.id)
                print("SENDING RESPONSE '{}'".format(ask_gift_response))
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown=ask_gift_response)
            elif "/want" in message.text and time.time() > LAST_DAY_TO_REGISTER:
                print("FOUND '/want'")
                gift = message.text.split('/want')[1].strip()
                # Get a response
                want_gift_response = want_gift(person.id, gift)
                print("SENDING RESPONSE '{}'".format(want_gift_response))
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown=want_gift_response)
            elif "/bought" in message.text and time.time() > LAST_DAY_TO_REGISTER:
                print("FOUND '/bought'")
                # Get a response
                bought_gift_response = bought_gift(person.id)
                print("SENDING RESPONSE '{}'".format(bought_gift_response))
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown=bought_gift_response)
            elif "/placed" in message.text and time.time() > LAST_DAY_TO_REGISTER:
                print("FOUND '/placed'")
                # Get a response
                placed_gift_response = placed_gift(person.id)
                print("SENDING RESPONSE '{}'".format(placed_gift_response))
                # Post the response to the room where the request was received
                api.messages.create(room.id, markdown=placed_gift_response)
            else:
                if time.time() <= LAST_DAY_TO_REGISTER:
                    api.messages.create(room.id, markdown='You need to register yourself by sending **/start** message to me')
                elif time.time() > LAST_DAY_TO_REGISTER and time.time() < CHRISTMAS_DATE:
                    api.messages.create(room.id, markdown='Please follow my instructions I have sent to you')
                    api.messages.create(room.id, markdown='If you bought a gift please send **/bought** message')
                    api.messages.create(room.id, markdown='If you placed a gift under a Christmas tree please send **/placed** message')
                    api.messages.create(room.id, markdown='You may ask me what gift I can suggest you to buy by sending **/ask** message to me')
                elif time.time() >= CHRISTMAS_DATE and time.time() < AFTER_CHRISTMAS_DATE:
                    api.messages.create(room.id, markdown='Merry Christmas!')
                elif time.time() >= AFTER_CHRISTMAS_DATE:
                    api.messages.create(room.id, markdown='I am on vacation')
                return 'OK'


if __name__ == '__main__':
    # Start the Flask web server
    flask_app.run(host='0.0.0.0', port=5000)