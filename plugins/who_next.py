import logging
import sys
import sqlite3
import re, json
import slack

from datetime import datetime
from slackbot.bot import respond_to, listen_to
from slackbot_settings import API_TOKEN
from setup_logging import logger
from plugins.singles_database_functions import *
from plugins.doubles_database_functions import *
from random import choice
from plugins.elo import elo, expected


@listen_to("^gb who next$", re.IGNORECASE)
def who_next(message):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    requester_id = message.body["user"]

    requester_name = str(channel_users[requester_id]["profile"]["real_name"])

    conn = create_connection(DATABASE_FILE)
    local_results = location_rankings(conn, location)
    if not local_results:
        local_results = full_rankings(conn)
    players = [x.user_id for x in local_results]

    next_player = choice(players)
    if next_player == requester_id:
        players.remove(requester_id)
        next_player = choice(players)

    logger.info("Who Next message requested by %s", requester_name)

    message.reply(
        "<@{}>, you should play <@{}> next".format(requester_id, next_player), in_thread=True
    )
