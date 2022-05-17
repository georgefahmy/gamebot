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


@listen_to("^gb new player <@(.*)>", re.IGNORECASE)
def add_new_player(message, new_player_id):
    channel_users = message.channel._client.users
    new_player_real_name = str(channel_users[new_player_id]["profile"]["real_name"])

    conn = create_connection(DATABASE_FILE)
    initialize_new_player(conn, new_player_id, new_player_real_name, channel_id=location)
    message.react("white_check_mark")


@listen_to(
    "^gb add game\s*<@(.*)>\s*<@(.*)>\s*([0-9]+)\s*-\s*([0-9]+)", re.IGNORECASE,
)
def add_new_game_entry(
    message, requester_id, opponent_id, wins, losses, channel_id=None, channel_name=None
):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_users = message.channel._client.users

    if not channel_id:
        channel_id = message.body["channel"]
    if not channel_name:
        channel_name = message.channel._body["name"]

    location = channel_id
    game_date = str(datetime.now()).split(".")[0]

    requester_name = str(channel_users[requester_id]["profile"]["real_name"])
    opponent_name = str(channel_users[opponent_id]["profile"]["real_name"])

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
    logger.info("Successfully added new games")

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


@listen_to(
    "^gb\s*add\s*doubles\s*game\s*<@(.*)>\s*<@(.*)>\s*([0-9]+)\s*-\s*([0-9]+)\s*<@(.*)>\s*<@(.*)>",
    re.IGNORECASE,
)
def add_doubles_game(
    message,
    team_1_player_1_id,
    team_1_player_2_id,
    wins,
    losses,
    team_2_player_1_id,
    team_2_player_2_id,
):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    # Team 1
    team_1_ids_list = sorted(
        [team_1_player_1_id.replace(" ", "_"), team_1_player_2_id.replace(" ", "_")]
    )

    team_1_player_1 = str(channel_users[team_1_ids_list[0]]["profile"]["real_name"])
    team_1_player_2 = str(channel_users[team_1_ids_list[1]]["profile"]["real_name"])

    team_1_team_ids = "-".join(team_1_ids_list)
    team_1_team_name = "-".join(
        [team_1_player_1.replace(" ", "_"), team_1_player_2.replace(" ", "_")]
    )
    logger.info("Team 1 IDs and Team Name: %s, %s", team_1_team_ids, team_1_team_name)

    # Team 2
    team_2_ids_list = sorted(
        [team_2_player_1_id.replace(" ", "_"), team_2_player_2_id.replace(" ", "_")]
    )

    team_2_player_1 = str(channel_users[team_2_ids_list[0]]["profile"]["real_name"])
    team_2_player_2 = str(channel_users[team_2_ids_list[1]]["profile"]["real_name"])

    team_2_team_ids = "-".join(team_2_ids_list)
    team_2_team_name = "-".join(
        [team_2_player_1.replace(" ", "_"), team_2_player_2.replace(" ", "_")]
    )
    logger.info("Team 2 IDs and Team Name: %s, %s", team_2_team_ids, team_2_team_name)

    game_date = str(datetime.now()).split(".")[0]

    conn = create_connection(DATABASE_FILE)
    team_a = return_doubles_results(conn, team_1_team_ids)
    team_b = return_doubles_results(conn, team_2_team_ids)

    if not team_a:
        logger.info("New team found, creating entry in database")
        team_a = initialize_new_team(
            conn,
            team_1_player_1,
            team_1_player_1_id,
            team_1_player_2,
            team_1_player_2_id,
            team_1_team_name,
            team_1_team_ids,
            wins=0,
            losses=0,
            total=0,
            ranking=1000,
            channel_id=location,
        )
    if not team_b:
        logger.info("New team found, creating entry in database")
        team_b = initialize_new_team(
            conn,
            team_2_player_1,
            team_2_player_1_id,
            team_2_player_2,
            team_2_player_2_id,
            team_2_team_name,
            team_2_team_ids,
            wins=0,
            losses=0,
            total=0,
            ranking=1000,
            channel_id=location,
        )

    old_team_a_ranking = team_a.ranking
    old_team_b_ranking = team_b.ranking

    def win_loss(team_a, team_b, win=True):
        team_a = return_doubles_results(conn, team_a.team_name_ids)
        team_b = return_doubles_results(conn, team_b.team_name_ids)
        team_a.location = team_a.location.split(", ")
        team_b.location = team_b.location.split(", ")
        team_a.location.append(location)
        team_b.location.append(location)

        if team_a.location[0] == "":
            team_a.location = "".join(list(set(team_a.location))[-1])
        else:
            team_a.location = ", ".join(list(set(team_a.location)))

        if team_b.location[0] == "":
            team_b.location = "".join(list(set(team_b.location))[-1])
        else:
            team_b.location = ", ".join(list(set(team_b.location)))

        if win:
            team_a.ranking, team_b.ranking = elo(team_a.ranking, team_b.ranking)
            team_a.wins += 1
            team_a.total += 1
            team_b.losses += 1
            team_b.total += 1
            doubles_results = (
                team_a.team_name,
                team_a.team_name_ids,
                team_b.team_name,
                team_b.team_name_ids,
                location,
                game_date,
            )
        else:
            team_b.ranking, team_a.ranking = elo(team_b.ranking, team_a.ranking)
            team_a.losses += 1
            team_a.total += 1
            team_b.wins += 1
            team_b.total += 1
            doubles_results = (
                team_b.team_name,
                team_b.team_name_ids,
                team_a.team_name,
                team_a.team_name_ids,
                location,
                game_date,
            )
        with conn:
            add_doubles_result(conn, doubles_results)
            update_doubles_rank(conn, tuple(team_a.__dict__.values()))
            update_doubles_rank(conn, tuple(team_b.__dict__.values()))

        return team_a, team_b

    # For the wins and losses, run through the win_loss function to update the games and rankings
    for i in range(int(wins)):
        team_a, team_b = win_loss(team_a, team_b, win=True)
    for i in range(int(losses)):
        team_a, team_b = win_loss(team_a, team_b, win=False)

    logger.info("Updated winner and loser rankings")

    team_a_rank_delta = round(team_a.ranking - old_team_a_ranking, 0)
    team_b_rank_delta = round(team_b.ranking - old_team_b_ranking, 0)

    team_a_rank_delta = (
        "{}".format(team_a_rank_delta) if team_a_rank_delta < 0 else "+{}".format(team_a_rank_delta)
    )
    team_b_rank_delta = (
        "{}".format(team_b_rank_delta) if team_b_rank_delta < 0 else "+{}".format(team_b_rank_delta)
    )
    team_a_string = (
        team_a.team_name
        + " "
        + str(round(old_team_a_ranking, 0))
        + " -> "
        + str(round(team_a.ranking, 0))
        + " ("
        + team_a_rank_delta
        + ")"
    )
    team_b_string = (
        team_b.team_name
        + " "
        + str(round(old_team_b_ranking, 0))
        + " -> "
        + str(round(team_b.ranking, 0))
        + " ("
        + team_b_rank_delta
        + ")"
    )
    ranking_response = team_a_string + "\n" + team_b_string + "\n\n"

    doubles_rankings = local_doubles_rankings(conn, location)

    logger.info("Retrieved local doubles rankings")

    def doubles_mini_leaderboard(team):
        team_strings = []
        team_index = [x.team_name for x in doubles_rankings].index(team.team_name)
        if team_index == 0:
            team_indecies = [0, 3]
        else:
            team_indecies = [team_index - 1, team_index + 2]

        i = team_indecies[0] + 1

        for team in doubles_rankings[team_indecies[0] : team_indecies[1]]:
            team_strings.append(
                "{}#{} {} ({}): {}/{} ({}%)".format(
                    "-> " if i - 1 == team_index else "      ",
                    i,
                    team.team_name,
                    team.ranking,
                    team.wins,
                    team.losses,
                    round(team.wins / team.total * 100, 1) if team.total > 0 else 0.0,
                )
            )
            i += 1
        team_strings.append("\n")
        doubles_mini_leaderboard = "\n".join(team_strings)
        return doubles_mini_leaderboard

    team_a_mini_leaderboard = doubles_mini_leaderboard(team_a)
    team_b_mini_leaderboard = doubles_mini_leaderboard(team_b)

    message_response = ranking_response + team_a_mini_leaderboard + team_b_mini_leaderboard

    message.react("white_check_mark")

    if wins == losses:
        message.react(emoji_mapping[wins])
    else:
        message.react(emoji_mapping[wins])
        message.react(emoji_mapping[losses])

    if int(wins) == 1 and int(losses) != 1:
        intro = "Recorded {} win and {} losses against <@{}>\n\n".format(
            wins, losses, team_b.team_name
        )
    elif int(wins) != 1 and int(losses) == 1:
        intro = "Recorded {} wins and {} loss against <@{}>\n\n".format(
            wins, losses, team_b.team_name
        )
    elif int(wins) == 1 and int(losses) == 1:
        intro = "Recorded {} win and {} loss against <@{}>\n\n".format(
            wins, losses, team_b.team_name
        )
    else:
        intro = "Recorded {} wins and {} losses against <@{}>\n\n".format(
            wins, losses, team_b.team_name
        )
    message_response = intro + message_response
    message.reply(message_response, in_thread=True)
    logger.info("Successfully added results and responded with mini leaderboard")


@listen_to(
    "pong new ranking\s*<@(.*)>\s*wins:\s*([0-9]+)\s*losses:\s*([0-9]+)\s*ranking:\s*([0-9]+)\s*channel:\s*<#([0-9a-zA-Z]+)\|([a-zA-z\s\-\_]*)>",
    re.IGNORECASE,
)
@listen_to(
    "pong new ranking\s*<@(.*)>\s*([0-9]+)\s*([0-9]+)\s*([0-9]+)", re.IGNORECASE,
)
def new_player_ranking(
    message, user_id, wins=0, losses=0, ranking=1000, channel_id=None, channel_name=None
):
    message_text = message.body["text"]
    message_time = message.body["ts"]
    logger.info(message_text)
    channel_users = message.channel._client.users

    if not channel_id:
        channel_id = "CAG4W7MCZ"
    if not channel_name:
        channel_name = "ping-pong"

    location = channel_id

    real_name = str(channel_users[user_id]["profile"]["real_name"])

    total = str(int(wins) + int(losses))
    conn = create_connection(DATABASE_FILE)
    initialize_new_player(
        conn,
        user_id,
        real_name,
        wins=wins,
        losses=losses,
        total=total,
        ranking=ranking,
        channel_id=location,
    )
    logger.info("SUCCESS!")
    return
