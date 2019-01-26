# -*- coding: utf-8 -*-

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os # for file with graph removal

import logging
import yaml

from scripts import setinitial

logger = logging.getLogger(__name__) # Creating logger for logging across this module

def action(subject=None, htmlBody="", email_list = [], attached_photo=None, files=[], email_test = False,
           email_to = ''):
        """
        This script allows you to send a HTML email. Eg: useful when you want to send preformatted text, etc,
        with all the flexibility of html to build the body

        :param email_test whether send email to test email or not

        Parameters:
          <addrFrom> From email address
          <addrTo> To email address (comma separated)
          <addrCc> Cc email address (comma separated)
          <subject> Email subject
          <htmlBody> Email body. Include any html tags you need.

        Returns:
        - None. Email just sent.
        """



        logger.info("Start loading config file")
        config = {}  # create dictionary for config
        try:
            config = setinitial.setup_config("config/config_marketing.yml")  # populate config from yaml file
        except yaml.YAMLError as exc:
            logger.fatal("Error in yaml file: " + str(exc))
            exit(2)
        except IOError as exc:
            logger.fatal("IOError:" + str(exc))
            exit(2)


        try:
            config["addrCc"]
        except KeyError:
            addrCc = None
            logger.info("Email will be sent without CC")
        else:
            addrCc = config["addrCc"]
            logger.info("Email will be sent with CC")

        try:  # Get mail login
            config["mail_login"]
        except KeyError:
            logger.info("Not found mail_login, will not use authentication")
            mail_login = None
            mail_pass = None
        else:
            mail_login = config["mail_login"]
            try:  # Get mail password
                config["mail_pass"]
            except KeyError:
                mail_pass = None
            else:
                mail_pass = config["mail_pass"]

        try:  # Get SMTP port
            config["smtp_port"]
        except KeyError:
            smtp_port = 25
        else:
            smtp_port = config["smtp_port"]

        addrFrom = config["addrFrom"]

        if email_test:
            logger.info('Using test email to:{}'.format(str(config["addrTo_test"])))

            # Add ignore disclaimer to the start of email message
            logger.info('Adding ignore disclaimer to the start of email message')
            email_list.insert(0,'<font color="red">Cообщение ниже ТЕСТОВОЕ, пожалуйста игнорируйте его!</font><br>')

            addrTo = config["addrTo_test"]



        elif not email_to: # if email address was not overrided in function call
            logger.info('Using standard email to:{}'.format(str(config["addrTo"])))
            addrTo = config["addrTo"]

        elif email_to:
            logger.info('Using overrided email to:{}'.format(str(email_to)))
            addrTo = email_to

        #Mail server
        smtp_server = config["smtp_server"]

        # Create the root message and fill in the from, to, and subject headers
        msgRoot = MIMEMultipart('related')
        msgRoot['To'] = addrTo
        if addrCc:
            msgRoot['Cc'] = addrCc
            msgRoot['From'] = addrFrom
        if subject:
            msgRoot['Subject'] = subject
        else:
            msgRoot['Subject'] = "CRC check test"

        msgRoot.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        #msgText = MIMEText('This is the alternative plain text message.')
        #msgAlternative.attach(msgText)

        if email_list:
            for row in email_list:
                htmlBody += '{}<br>'.format(row)

        #if htmlBody:
            #pass
            #txtEmail = MIMEText(htmlBody.decode('utf-8'), 'plain', 'UTF-8')
            #htmlEmail = MIMEText(htmlBody.decode('utf-8'), 'html', 'UTF-8')
            #msgAlternative.attach(htmlEmail)
            #msgRoot.attach(htmlEmail)

        if attached_photo:
            try:

                #msgRoot.attach(msgText)  # Added

                fp = open(attached_photo, 'rb')
                img = MIMEImage(fp.read())
                fp.close()


            except IOError:
                logger.error("No file with topology found, skipping it addition")
            else:

                htmlBody += "<b>Received photo:</b>"

                if htmlBody:
                    # Add html text and picture
                    # We reference the image in the IMG SRC attribute by the ID we give it below

                    #msgText = MIMEText(htmlBody.decode('utf-8') +
                    #                   '<br><img src="cid:{}"><br>'.format("image1"), 'html', 'UTF-8')
                    htmlBody += '<br><img src="cid:{}"><br>'.format("image1")


                else:
                    # Add only picture
                    htmlBody = '<br><img src="cid:{}"><br>'.format("image1")


                # Define the image's ID as referenced above
                img.add_header('Content-ID', '<image1>')
                msgRoot.attach(img)

                img.add_header('Content-Disposition', 'attachment', filename="Topology.jpg")
                msgRoot.attach(img)
                ##htmlBody += "<b>Топология:</b>"
                #htmlBody += "You can find topology of the segment in attach<br><br>"
                #htmlBody += "Топология сегмента во вложении<br><br>"
                #htmlBody += '<br><img src="{}"><br>'.format(topologyImage)

                #msgText = MIMEText('<br><img src="{}"><br>'.format(topologyImage), 'html')
                #msg.attach(msgText)  # Added, and edited the previous line


        # add footer
        htmlBody += '<font color="#808080"><em>WebexTeamsBots Lab CiscoLive2019. Barcelona</em></font>'

        #msgText = MIMEText(htmlBody.decode('utf-8'), 'html', 'UTF-8')
        msgText = MIMEText(htmlBody, 'html', 'UTF-8')
        msgAlternative.attach(msgText)  # Add msgText to letter

        for f in files:
            part = MIMEBase('application', "octet-stream")
            part.set_payload(open(f, "rb").read())
            part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(f)))
            msgRoot.attach(part)




        # Send it


        #s = smtplib.SMTP(smtp_server,smtp_port) #Use SMTP port 25 by default
        s = smtplib.SMTP_SSL(smtp_server, smtp_port)  # Use SMTP port 25 by default
        logger.info("SMTP server=" + smtp_server + " port=" + str(smtp_port))

        #if (mail_login != None and mail_pass != None):
        if mail_login != None:
            #s.ehlo()
            #s.starttls()
            #s.ehlo
            #s.login(mail_login,mail_pass) # In case we need authentication
            ##s.helo(mail_login)
            ##logger.info("Email login=" + str(mail_login))
            s.ehlo()
            s.login(mail_login, mail_pass)


        else:
            logger.info("Email without authentication")

        if addrCc: # send email with CC
            s.sendmail(addrFrom, addrTo.split(",") + addrCc.split(","), msgRoot.as_string()) #str.split already converts comma separated strings to list, which is what we need
            logger.info("Email Sent to:" + addrFrom + "->" + addrTo +"(" + addrCc +")" + ":" + "\""+ subject + "\"")
        else: # send email without CC
            s.sendmail(addrFrom, addrTo.split(","), msgRoot.as_string())
            logger.info("Email Sent to:" + addrFrom + "->" + addrTo + ":" + "\""+ subject + "\"")
        s.quit()
