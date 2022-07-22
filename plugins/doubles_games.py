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


@listen_to("^gb doubles <@(.*)>\s*([0-9]+)\s*-\s*([0-9]+)\s*<@(.*)>\s*<@(.*)>", re.IGNORECASE)
def double_results(message, teammate_id, wins, losses, opponent_a_id, opponent_b_id):
    message_text = message.body["text"]
    message_time = message.body["ts"]

    channel_name = message.channel._body["name"]
    channel_id = message.body["channel"]
    channel_users = message.channel._client.users

    location = channel_id

    # Team 1
    team_1_player_1_id = message.body["user"]
    team_1_player_2_id = teammate_id

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
    team_2_player_1_id = opponent_a_id
    team_2_player_2_id = opponent_b_id

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
    if int(wins) > 9 or int(losses) > 9:
        message.react("wow")

    elif 0 <= int(wins) <= 9:
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
