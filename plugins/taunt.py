import logging
import sys
import sqlite3
import re, json
import slack
import urllib
import requests

from datetime import datetime
from random import choice
from slackbot.bot import respond_to, listen_to
from slackbot_settings import API_TOKEN, GIPHY_API
from setup_logging import logger
from plugins.singles_database_functions import *
from plugins.doubles_database_functions import *
from plugins.elo import elo, expected

GIPHY_URL = "http://api.giphy.com/v1/gifs/search"
params = urllib.parse.urlencode(
    {"api_key": GIPHY_API, "q": "ping pong taunt", "limit": 25, "rating": "g", "lan": "en"}
)
url = GIPHY_URL + "?" + params
data = json.loads(requests.get(GIPHY_URL + "?" + params).content)["data"]


@listen_to("^gb taunt\s*<@([a-zA-Z0-9]+)>$", re.IGNORECASE)
def taunt(message, opponent_id=None):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    requester_id = message.body["user"]

    requester_name = str(channel_users[requester_id]["profile"]["real_name"])
    opponent_name = str(channel_users[opponent_id]["profile"]["real_name"])

    conn = create_connection(DATABASE_FILE)
    logger.info("requester: %s, taunts opponent: %s", requester_name, opponent_name)

    player_a = return_results(conn, requester_id)
    if not player_a:
        logger.info("New player found, creating entry in database")
        player_a = initialize_new_player(conn, requester_id, requester_name, channel_id=location)
    player_b = return_results(conn, opponent_id)
    if not player_b:
        logger.info("New player found, creating entry in database")
        player_b = initialize_new_player(conn, opponent_id, opponent_name, channel_id=location)

    random_gif_url = choice(data)["url"]
    response = f"<@{player_b.user_id}>, you have been taunted...\n {random_gif_url}"
    message.reply(response, in_thread=True)
