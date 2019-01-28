import logging
from flask import Flask, request
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

from bot import process_message as ssbot_process_message
from utils import webhook
from utils import setinitial

# Initializing logger
setinitial.setup_logging()
# Create logger
logger = logging.getLogger(__name__)

config = {}  # create dictionary for config
try:
    config = setinitial.setup_config('config/config_service.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)


# Initialize the environment

# Create the web application instance


# Your WebEx Teams webhook should point to http://<serverip>:5000/events
# webex_teams_webhook_events() function goes here (with decorator)

# main function code goes here
