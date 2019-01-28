from flask import Flask, request
from bot import process_message as markbot_process_message
import logging
from webexteamssdk import WebexTeamsAPI, Webhook, Message, Room

from utils import setinitial
from utils import PSQL_marketing
from utils.tasker_marketing import Tasker
from utils import emailsend2
from utils import webhook


# Initialize the environment
# Create the web application instance
flask_app = Flask(__name__)


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

# Your WebEx Teams webhook should point to http://<serverip>:5000/events
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
                   Marketing campain:
                   </p>
                   <blockquote>Santa Quest</blockquote>
                   </body>
                   </html>
                """)
    elif request.method == 'POST':
        """Responds to inbound webhook JSON HTTP POST from Webex Teams."""

        # Get the POST data sent from Webex Teams
        logger.info('WEBHOOK POST RECEIVED:')
        logger.info(request.json)

        return markbot_process_message(api,config,request.json)

# Approver URI


@flask_app.route('/approve_content', methods=['GET', 'POST'])
def update_task():

    try:
        psql_obj = PSQL_marketing.PSQL('ciscolive', config["db_host"],
                             config["db_login"], config["db_password"])
    except IndexError:
        logger.fatal(f'Can\'t connect to Database:{config["db_login"]}@{config["db_host"]}/ciscolive')
        exit(2)

    logger.info(f'Connected to DB:{config["db_login"]}@{config["db_host"]}/ciscolive')

    person_id = request.args.get('person_id')
    task_id = request.args.get('task_id')
    epoch = request.args.get('epoch')

    is_approved = request.args.get('approved')

    logger.info(f'Got:{person_id}/{task_id}/{epoch}/{is_approved}')

    if is_approved == 'True':
        Tasker.change_content_status(psql_obj,person_id,task_id,epoch,'approved')
    elif is_approved == 'False':
        Tasker.change_content_status(psql_obj, person_id, task_id, epoch,'rejected')
    else:
        return 'Error:Unknow status'

    return 'OK'


if __name__ == '__main__':
    logger.info(f'Start using token:{config["bot_access_token"]}')
    api = WebexTeamsAPI(config['bot_access_token'])
    webhook_name = config['webhook_name']

    """Delete previous webhooks. If local ngrok tunnel, create a webhook."""
    if webhook.create_webhook(api,config['webhook_name']):
        ngrok_port = webhook.get_ngrok_port()
        logger.info(f'Get ngrok port={ngrok_port}.Starting Flask server on it')

        # Start the Flask web server
        flask_app.run(host='0.0.0.0', port=ngrok_port)
    else:
        logger.fatal('Can\'t create webhook for WebexTeams')
