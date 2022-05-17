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

# TODO singles game prediction

emoji_mapping = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


@listen_to("^gb results\s*<@(.*)>\s*([0-9]+)\s*-\s*([0-9]+)\s*", re.IGNORECASE)
@listen_to("^gb result\s*<@(.*)>\s*([0-9]+)\s*-\s*([0-9]+)\s*", re.IGNORECASE)
@listen_to("^gb singles\s*<@(.*)>\s*([0-9]+)\s*-\s*([0-9]+)\s*", re.IGNORECASE)
def singles_results(message, opponent_id, wins, losses):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    requester_id = message.body["user"]

    requester_name = str(channel_users[requester_id]["profile"]["real_name"])
    opponent_name = str(channel_users[opponent_id]["profile"]["real_name"])
    game_date = str(datetime.now()).split(".")[0]
    logger.info("New Result message by %s", requester_name)

    if requester_id == opponent_id:
        response = "ERROR: Oppenent must be a different person than yourself..."
        message.reply(response, in_thread=True)
        return

    conn = create_connection(DATABASE_FILE)
    player_a = return_results(conn, requester_id)
    player_b = return_results(conn, opponent_id)

    if not player_a:
        logger.info("New player found, creating entry in database")
        player_a = initialize_new_player(conn, requester_id, requester_name, channel_id=location)
    if not player_b:
        logger.info("New player found, creating entry in database")
        player_b = initialize_new_player(conn, opponent_id, opponent_name, channel_id=location)

    old_player_a_ranking = player_a.ranking
    old_player_b_ranking = player_b.ranking

    def win_loss(player_a, player_b, win=True):
        player_a = return_results(conn, player_a.user_id)
        player_b = return_results(conn, player_b.user_id)
        player_a.location = player_a.location.split(", ")
        player_b.location = player_b.location.split(", ")
        player_a.location.append(location)
        player_b.location.append(location)

        if player_a.location[0] == "":
            player_a.location = "".join(list(set(player_a.location))[-1])
        else:
            player_a.location = ", ".join(list(set(player_a.location)))

        if player_b.location[0] == "":
            player_b.location = "".join(list(set(player_b.location))[-1])
        else:
            player_b.location = ", ".join(list(set(player_b.location)))

        if win:
            player_a.ranking, player_b.ranking = elo(player_a.ranking, player_b.ranking)
            player_a.wins += 1
            player_a.total += 1
            player_b.losses += 1
            player_b.total += 1
            singles_results = (
                player_a.real_name,
                player_a.user_id,
                player_b.real_name,
                player_b.user_id,
                location,
                game_date,
            )
        else:
            player_b.ranking, player_a.ranking = elo(player_b.ranking, player_a.ranking)
            player_a.losses += 1
            player_a.total += 1
            player_b.wins += 1
            player_b.total += 1
            singles_results = (
                player_b.real_name,
                player_b.user_id,
                player_a.real_name,
                player_a.user_id,
                location,
                game_date,
            )
        with conn:
            add_singles_result(conn, singles_results)
            update_singles_rank(conn, tuple(player_a.__dict__.values()))
            update_singles_rank(conn, tuple(player_b.__dict__.values()))

        return player_a, player_b

    for i in range(int(wins)):
        player_a, player_b = win_loss(player_a, player_b, win=True)
    for i in range(int(losses)):
        player_a, player_b = win_loss(player_a, player_b, win=False)

    logger.info("Updated winner and loser rankings")

    player_a_rank_delta = round(player_a.ranking - old_player_a_ranking, 0)
    player_b_rank_delta = round(player_b.ranking - old_player_b_ranking, 0)

    player_a_rank_delta = (
        "{}".format(player_a_rank_delta)
        if player_a_rank_delta < 0
        else "+{}".format(player_a_rank_delta)
    )
    player_b_rank_delta = (
        "{}".format(player_b_rank_delta)
        if player_b_rank_delta < 0
        else "+{}".format(player_b_rank_delta)
    )
    player_a_string = (
        player_a.real_name
        + " "
        + str(round(old_player_a_ranking, 0))
        + " -> "
        + str(round(player_a.ranking, 0))
        + " ("
        + player_a_rank_delta
        + ")"
    )
    player_b_string = (
        player_b.real_name
        + " "
        + str(round(old_player_b_ranking, 0))
        + " -> "
        + str(round(player_b.ranking, 0))
        + " ("
        + player_b_rank_delta
        + ")"
    )

    ranking_response = player_a_string + "\n" + player_b_string + "\n\n"

    rankings = location_rankings(conn, location)
    logger.info("Retrieved local rankings")

    def mini_leaderboard(player):
        player_strings = []
        player_index = [x.real_name for x in rankings].index(player.real_name)
        if player_index == 0:
            player_indecies = [0, 3]
        else:
            player_indecies = [player_index - 1, player_index + 2]

        i = player_indecies[0] + 1

        for player in rankings[player_indecies[0] : player_indecies[1]]:
            player_strings.append(
                "{}#{} {} ({}): {}/{} ({}%)".format(
                    "-> " if i - 1 == player_index else "      ",
                    i,
                    player.real_name,
                    player.ranking,
                    player.wins,
                    player.losses,
                    round(player.wins / player.total * 100, 1) if player.total > 0 else 0.0,
                )
            )
            i += 1
        player_strings.append("\n")
        mini_leaderboard = "\n".join(player_strings)
        return mini_leaderboard

    player_a_mini_leaderboard = mini_leaderboard(player_a)
    player_b_mini_leaderboard = mini_leaderboard(player_b)

    message_response = ranking_response + player_a_mini_leaderboard + player_b_mini_leaderboard

    message.react("white_check_mark")
    if wins == losses:
        message.react(emoji_mapping[wins])
    else:
        message.react(emoji_mapping[wins])
        message.react(emoji_mapping[losses])
    if int(wins) == 1 and int(losses) != 1:
        intro = "Recorded {} win and {} losses against <@{}>\n\n".format(
            wins, losses, player_b.user_id
        )
    elif int(wins) != 1 and int(losses) == 1:
        intro = "Recorded {} wins and {} loss against <@{}>\n\n".format(
            wins, losses, player_b.user_id
        )
    elif int(wins) == 1 and int(losses) == 1:
        intro = "Recorded {} win and {} loss against <@{}>\n\n".format(
            wins, losses, player_b.user_id
        )
    else:
        intro = "Recorded {} wins and {} losses against <@{}>\n\n".format(
            wins, losses, player_b.user_id
        )
    message_response = intro + message_response
    message.reply(message_response, in_thread=True)
    logger.info("Successfully added results and responded with mini leaderboard")
