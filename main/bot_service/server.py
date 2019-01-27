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
flask_app = Flask(__name__)


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
                   <strong>Service bot</strong>
                   </p>
                   </body>
                   </html>
                """)
    elif request.method == 'POST':
        """Responds to inbound webhook JSON HTTP POST from Webex Teams."""

        # Get the POST data sent from Webex Teams
        logging.info('WEBHOOK POST RECEIVED:')
        logging.info(request.json)

        return ssbot_process_message(api,request.json)


if __name__ == '__main__':
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
