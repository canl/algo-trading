import smtplib, ssl
from email.mime.multipart import MIMEMultipart
import logging
import configparser
import os
from email.mime.text import MIMEText

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def compose_email(sender, recipients, subject, body):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipients
    msg['Subject'] = subject
    content = MIMEText(body, "html")
    msg.attach(content)
    return msg


def notify(subject: str, body: str):
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'conf', 'mail.cfg'))
    sender = config['gmail']['account']
    recipients = config['gmail']['recipients']
    logger.info(f"Sending email to [{recipients}] with account: [{sender}]")
    message = compose_email(sender, recipients, subject, body)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, config['gmail']['password'])
            server.sendmail(sender, recipients.split(','), message.as_string())
        logger.info(f"Email successfully sent to {recipients}")

    except Exception as ex:
        logger.error(f'Failed to send out alerts with error {ex}')


if __name__ == '__main__':
    # pass
    notify('thi is a test', 'my test')
