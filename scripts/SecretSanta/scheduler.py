import sched
import time
from webexteamssdk import WebexTeamsAPI
from random import shuffle
from dates import *
import json

scheduler = sched.scheduler(time.time, time.sleep)
api = WebexTeamsAPI(access_token='MGZjOGFkNGUtNmQ5OC00Y2UzLWE0MjktNjAyYmNhMzBmOTQwNThhZGU3NjctNWYy')


def shuffle_users():
    with open("users.json", "r") as read_file:
        json_users = json.load(read_file)

    shuffle(json_users)

    for index, json_user in enumerate(json_users):
        if index + 1 < len(json_users):
            json_user['pair'] = json_users[index + 1]['id']
        elif index == len(json_users) - 1:
            json_user['pair'] = json_users[0]['id']

    with open("users.json", "w") as write_file:
        json.dump(json_users, write_file)


def non_bought_users():
    json_users = []
    try:
        with open("users.json", "r") as read_file:
            json_users = json.load(read_file)
    except:
        json_users = []
    for index, user in enumerate(json_users):
        if not user['bought']:
            gift = ''
            for pair_index, user in enumerate(json_users):
                if user['id'] == json_users[index]['pair']:
                    break
            else:
                pair_index = -1
            gift = json_users[pair_index]['gift']
            if gift:
                api.messages.create(user['room'], markdown='You need to buy **'+gift+'** to your pair')
            else:
                api.messages.create(user['room'], markdown='You need to buy a gift to your pair')
            api.messages.create(user['room'], markdown='If you bought a gift already please send a confirmation by **/bought** command')

def non_placed_users():
    json_users = []
    try:
        with open("users.json", "r") as read_file:
            json_users = json.load(read_file)
    except:
        json_users = []
    for user in json_users:
        if not user['placed']:
            api.messages.create(user['room'], markdown='You need to place a gift under Christmas tree')
            api.messages.create(user['room'], markdown='Once you placed it just reply with **/placed** command')


def take_gift():
    json_users = []
    try:
        with open("users.json", "r") as read_file:
            json_users = json.load(read_file)
    except:
        json_users = []
    for user in json_users:
        api.messages.create(user['room'], markdown='Take your gift under Christmas tree')


scheduler.enterabs(LAST_DAY_TO_REGISTER, 1, shuffle_users)
scheduler.enterabs(SEVENTH_DAY_BEFORE_CHRISTMAS, 1, non_bought_users)
scheduler.enterabs(SIXTH_DAY_BEFORE_CHRISTMAS, 1, non_bought_users)
scheduler.enterabs(FIFTH_DAY_BEFORE_CHRISTMAS, 1, non_bought_users)
scheduler.enterabs(FOURTH_DAY_BEFORE_CHRISTMAS, 1, non_bought_users)
scheduler.enterabs(THIRD_DAY_BEFORE_CHRISTMAS, 1, non_placed_users)
scheduler.enterabs(SECOND_DAY_BEFORE_CHRISTMAS, 1, non_placed_users)
scheduler.enterabs(ONE_DAY_BEFORE_CHRISTMAS, 1, take_gift)
scheduler.run()
