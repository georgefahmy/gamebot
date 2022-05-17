import logging
import sys
import sqlite3
import re, json
import slack

from slackbot.bot import respond_to, listen_to
from slackbot_settings import API_TOKEN
from setup_logging import logger
from plugins.singles_database_functions import *
from plugins.doubles_database_functions import *
from datetime import datetime
from plugins.elo import elo


@listen_to("^gb help", re.IGNORECASE)
def help(message):
    with open("plugins/help.txt", "r") as fp:
        # help_message = json.load(fp)["help"]
        help_message = fp.read()

    logger.info("Help message requested")
    message.reply(help_message, in_thread=True)
