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

# process_message() function goes here


# process_command() function goes here
