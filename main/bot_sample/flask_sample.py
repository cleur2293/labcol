from flask import Flask, request

# Initialize the environment

ngrok_port = 5000

# Create the web application instance
flask_app = Flask(__name__)

@flask_app.route('/events2', methods=['GET', 'POST'])
def webex_teams_webhook_events():
    """Processes incoming requests to the '/events' URI."""

    if request.method == 'GET':
        return ("""<!DOCTYPE html><html lang="en">
                       <head><meta charset="UTF-8"><title>ServiceBot</title></head>
                        <body>
                            <p><strong>Sample Bot running Flask2</strong></p>
                        </body>
                   </html>""")

    return 'OK'

if __name__ == '__main__':
    # Start the Flask web server
    flask_app.run(host='0.0.0.0', port=ngrok_port)
