import logging
import os
import sys
import inspect
from flask import Flask, request
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

#<put import process_message>
from utils import webhook
from utils import setinitial

# To be able to load modules from parent directory
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

# Initializing logger
setinitial.setup_logging()
# Create logger
logger = logging.getLogger(__name__)


config = {}  # create dictionary for config
try:
    config = setinitial.setup_config('../config/config_service.yml')  # populate config from yaml file
except yaml.YAMLError as exc:
    logger.fatal("Error in yaml file: " + str(exc))
    exit(2)
except IOError as exc:
    logger.fatal("IOError:" + str(exc))
    exit(2)


# Initialize the environment

# Create the web application instance
#<create flask instance>

#<create webhook events>

# main function code goes here
#<create main function>
