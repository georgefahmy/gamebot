import logging
import sys
import sqlite3
from sqlite3 import Error
import re, json
from setup_logging import logger
from collections import OrderedDict

# This is the database file to be used when establishing connections to the db
DATABASE_FILE = "pongbot_v2.db"


class Team:
    def __init__(self, team_dict):
        self.player_1 = team_dict["player_1"]
        self.player_1_id = team_dict["player_1_id"]
        self.player_2 = team_dict["player_2"]
        self.player_2_id = team_dict["player_2_id"]
        self.team_name = team_dict["team_name"]
        self.team_name_ids = team_dict["team_name_ids"]
        self.wins = team_dict["wins"]
        self.losses = team_dict["losses"]
        self.total = team_dict["total"]
        self.ranking = team_dict["ranking"]
        self.location = team_dict["location"]


class DoublesGame:
    def __init__(self, game_results):
        self.winning_team = game_results["winning_team"]
        self.winning_team_ids = game_results["winning_team_ids"]
        self.losing_team = game_results["losing_team"]
        self.losing_team_ids = game_results["losing_team_ids"]
        self.location = game_results["location"]
        self.game_date = game_results["game_date"]


# Function for creating the connection to the database file provided
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn


def add_doubles_result(conn, doubles_results):
    sql = """ INSERT INTO doubles_results_table(winning_team, winning_team_ids, losing_team, losing_team_ids, location, game_date)
              VALUES(?,?,?,?,?,?) """
    cur = conn.cursor()
    success = cur.execute(sql, doubles_results)
    conn.commit()
    return


def update_doubles_rank(conn, doubles_ranking):
    sql = """ UPDATE doubles_rankings_table SET wins=?, losses=?, total=?, ranking=?, location=? WHERE team_name_ids like ?
    """
    cur = conn.cursor()
    success = cur.execute(sql, (doubles_ranking[6:] + (doubles_ranking[5],)))
    conn.commit()
    return


def return_doubles_results(conn, team_name_ids):
    cur = conn.cursor()
    cur.execute("SELECT * FROM doubles_rankings_table WHERE team_name_ids LIKE ?", (team_name_ids,))
    results = cur.fetchall()
    if not results:
        return
    results = results[0]
    results = Team(
        {
            "player_1": results[1],
            "player_1_id": results[2],
            "player_2": results[3],
            "player_2_id": results[4],
            "team_name": results[5],
            "team_name_ids": results[6],
            "wins": results[7],
            "losses": results[8],
            "total": results[9],
            "ranking": results[10],
            "location": results[11],
        }
    )
    conn.commit()
    return results


def initialize_new_team(
    conn,
    player_1,
    player_1_id,
    player_2,
    player_2_id,
    team_name,
    team_name_ids,
    wins=0,
    losses=0,
    total=0,
    ranking=1000,
    channel_id=None,
):
    doubles_ranking = (
        player_1,
        player_1_id,
        player_2,
        player_2_id,
        team_name,
        team_name_ids,
        wins,
        losses,
        total,
        ranking,
        channel_id,
    )
    sql = """ INSERT OR IGNORE INTO doubles_rankings_table(
        player_1,
        player_1_id,
        player_2,
        player_2_id,
        team_name,
        team_name_ids,
        wins,
        losses,
        total,
        ranking,
        location
    )
              VALUES(?,?,?,?,?,?,?,?,?,?,?)"""
    cur = conn.cursor()
    success = cur.execute(sql, doubles_ranking)
    if success:
        logger.info("Successfully added new team")
    doubles_ranking = Team(
        {
            "player_1": player_1,
            "player_1_id": player_1_id,
            "player_2": player_2,
            "player_2_id": player_2_id,
            "team_name": team_name,
            "team_name_ids": team_name_ids,
            "wins": wins,
            "losses": losses,
            "total": total,
            "ranking": ranking,
            "location": channel_id,
        }
    )

    conn.commit()
    return doubles_ranking


def full_doubles_rankings(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM doubles_rankings_table ORDER by ranking DESC")
    results = cur.fetchall()
    if not results:
        return
    full_doubles_rankings = []
    for result in results:
        full_doubles_rankings.append(
            Team(
                {
                    "player_1": result[1],
                    "player_1_id": result[2],
                    "player_2": result[3],
                    "player_2_id": result[4],
                    "team_name": result[5],
                    "team_name_ids": result[6],
                    "wins": result[7],
                    "losses": result[8],
                    "total": result[9],
                    "ranking": result[10],
                    "location": result[11],
                }
            )
        )
    return full_doubles_rankings


def local_doubles_rankings(conn, location):
    location = ("%" + location + "%",)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM doubles_rankings_table where location LIKE ? ORDER by ranking DESC",
        location,
    )
    results = cur.fetchall()
    if not results:
        return
    local_doubles_rankings = []
    for result in results:
        local_doubles_rankings.append(
            Team(
                {
                    "player_1": result[1],
                    "player_1_id": result[2],
                    "player_2": result[3],
                    "player_2_id": result[4],
                    "team_name": result[5],
                    "team_name_ids": result[6],
                    "wins": result[7],
                    "losses": result[8],
                    "total": result[9],
                    "ranking": result[10],
                    "location": result[11],
                }
            )
        )
    return local_doubles_rankings


def full_doubles_history(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM doubles_results_table ORDER by game_date ASC")
    results = cur.fetchall()
    if not results:
        return
    doubles_history = []
    for result in results:
        doubles_history.append(
            DoublesGame(
                {
                    "winning_team": result[1],
                    "winning_team_ids": result[2],
                    "losing_team": result[3],
                    "losing_team_ids": result[4],
                    "location": result[5],
                    "game_date": result[6],
                }
            )
        )
    return doubles_history


def doubles_prediction_history(conn, requester_id, opponent_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM doubles_results_table WHERE (winning_team_ids = ? AND losing_team_ids = ? OR winning_team_ids = ? AND losing_team_ids = ?) ORDER by game_date ASC",
        (team_a_ids, team_b_ids, team_b_ids, team_a_ids),
    )
    results = cur.fetchall()
    if not results:
        return
    doubles_prediction_results = []
    for result in results:
        doubles_prediction_results.append(
            DoublesGame(
                {
                    "winning_team": result[1],
                    "winning_team_ids": result[2],
                    "losing_team": result[3],
                    "losing_team_ids": result[4],
                    "location": result[5],
                    "game_date": result[6],
                }
            )
        )
    return doubles_prediction_results
