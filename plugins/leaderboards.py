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


@listen_to("^gb\s*leaderboard", re.IGNORECASE)
@listen_to("^gb\s*full\s*leaderboard", re.IGNORECASE)
def local_leaderboard(message):
    message_text = message.body["text"]
    if "full" in message_text:
        local = False
        logger.info("Full Leaderboard requested")
    else:
        local = True
        logger.info("Local Leaderboard requested")

    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    requester_id = message.body["user"]
    requester_name = str(channel_users[requester_id]["profile"]["real_name"])
    logger.info("Leaderboard message requested by %s", requester_name)

    conn = create_connection(DATABASE_FILE)
    if local:
        rankings = location_rankings(conn, location)
    else:
        rankings = full_rankings(conn)

    if not rankings:
        message.reply("Leaderboard is Empty...Play some games!", in_thread=True)
        return

    player_strings = []

    for i, player in enumerate(rankings):
        player_strings.append(
            "#{} {} ({}): {}/{} ({}%)".format(
                i + 1,
                player.real_name,
                player.ranking,
                player.wins,
                player.losses,
                round(player.wins / player.total * 100, 1) if player.total > 0 else 0.0,
            )
        )
    player_strings.append("\n")
    intro = "Leaderboard\n"
    location_string = "Location: " + channel_name + "\n\n" if local else "\n\n"
    response = intro + location_string + "\n".join(player_strings)
    message.reply(response, in_thread=True)
    logger.info("Posted Response")


@listen_to("^gb\s*doubles\s*leaderboard", re.IGNORECASE)
@listen_to("^gb\s*doubles\s*full\s*leaderboard", re.IGNORECASE)
def local_leaderboard(message):
    message_text = message.body["text"]
    if "full" in message_text:
        local = False
        logger.info("Doubles full leaderboard requested")
    else:
        local = True
        logger.info("Doubles local leaderboard requested")

    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    requester_id = message.body["user"]
    requester_name = str(channel_users[requester_id]["profile"]["real_name"])
    logger.info("Leaderboard message requested by %s", requester_name)

    conn = create_connection(DATABASE_FILE)
    if local:
        rankings = local_doubles_rankings(conn, location)
    else:
        rankings = full_doubles_rankings(conn)
    if not rankings:
        message.reply("Leaderboard is Empty...Play some games!", in_thread=True)
        return

    team_strings = []

    for i, team in enumerate(rankings):
        team_strings.append(
            "#{} {} ({}): {}/{} ({}%)".format(
                i + 1,
                team.team_name,
                team.ranking,
                team.wins,
                team.losses,
                round(team.wins / team.total * 100, 1) if team.total > 0 else 0.0,
            )
        )
    team_strings.append("\n")
    intro = "Doubles Leaderboard\n"
    location_string = "Location: " + channel_name + "\n\n" if local else "\n\n"
    response = intro + location_string + "\n".join(team_strings)
    message.reply(response, in_thread=True)
    logger.info("Posted Response")
