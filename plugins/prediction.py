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
from plugins.elo import elo, expected


@listen_to("^gb predict\s*<@([a-zA-Z0-9]+)>\s*<@([a-zA-Z0-9]+)>$", re.IGNORECASE)
@listen_to("^gb predict\s*<@([a-zA-Z0-9]+)>$", re.IGNORECASE)
def predict(message, opponent_id=None, requester_id=None):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id
    if not requester_id:
        logger.warning("player b is empty, using the requester")
        requester_id = message.body["user"]

    requester_name = str(channel_users[requester_id]["profile"]["real_name"])
    opponent_name = str(channel_users[opponent_id]["profile"]["real_name"])

    conn = create_connection(DATABASE_FILE)
    logger.info("requester: %s, opponent: %s", requester_name, opponent_name)

    player_a = return_results(conn, requester_id)
    if not player_a:
        logger.info("New player found, creating entry in database")
        player_a = initialize_new_player(conn, requester_id, requester_name, channel_id=location)
    player_b = return_results(conn, opponent_id)
    if not player_b:
        logger.info("New player found, creating entry in database")
        player_b = initialize_new_player(conn, opponent_id, opponent_name, channel_id=location)

    games = prediction_history(conn, requester_id, opponent_id)
    if not games:
        games = []
        wins = 0
        losses = 0
    else:
        wins = 0
        losses = 0
        for game in games:
            if player_a.user_id == game.winner_id:
                wins += 1
            if player_a.user_id == game.loser_id:
                losses += 1
    wins_losses = "({}w - {}l) ".format(wins, losses) if wins or losses else ""
    exp = expected(player_a.ranking, player_b.ranking)
    response = "{} {}games played between <@{}> ({}) and <@{}> ({}).\n<@{}> is {}% likely to win the next game".format(
        len(games),
        wins_losses,
        player_a.user_id,
        player_a.ranking,
        player_b.user_id,
        player_b.ranking,
        player_a.user_id if exp > 50 else player_b.user_id,
        exp if exp > 50 else 100 - exp,
    )
    message.reply(response, in_thread=True)
