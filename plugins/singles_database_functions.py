import logging
import sys
import sqlite3
from sqlite3 import Error
import re, json
from setup_logging import logger
from collections import OrderedDict

# This is the database file to be used when establishing connections to the db
DATABASE_FILE = "pongbot_v2.db"


class Player:
    def __init__(self, player_dict):
        self.user_id = player_dict["user_id"]
        self.real_name = player_dict["real_name"]
        self.wins = player_dict["wins"]
        self.losses = player_dict["losses"]
        self.total = player_dict["total"]
        self.ranking = player_dict["ranking"]
        self.location = player_dict["location"]


class Game:
    def __init__(self, game_results):
        self.winner = game_results["winner"]
        self.winner_id = game_results["winner_id"]
        self.loser = game_results["loser"]
        self.loser_id = game_results["loser_id"]
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


def add_singles_result(conn, singles_results):
    sql = """ INSERT INTO singles_results_table(winner, winner_id, loser, loser_id, location, game_date)
              VALUES(?,?,?,?,?,?) """
    cur = conn.cursor()
    success = cur.execute(sql, singles_results)
    conn.commit()
    return


def update_singles_rank(conn, singles_ranking):
    sql = """ UPDATE singles_user_rankings SET wins=?, losses=?, total=?, ranking=?, location=?
              WHERE user_id like ?"""
    cur = conn.cursor()
    success = cur.execute(sql, (singles_ranking[2:] + (singles_ranking[0],)))
    conn.commit()
    return


def return_results(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM singles_user_rankings WHERE user_id LIKE ?", (user_id,))
    results = cur.fetchall()
    if not results:
        return
    results = results[0]
    results = Player(
        {
            "user_id": results[1],
            "real_name": results[2],
            "wins": results[3],
            "losses": results[4],
            "total": results[5],
            "ranking": results[6],
            "location": results[7],
        }
    )
    conn.commit()
    return results


def initialize_new_player(
    conn, user_id, real_name, wins=0, losses=0, total=0, ranking=1000, channel_id=None
):
    singles_ranking = (user_id, real_name, wins, losses, total, ranking, channel_id)
    sql = """ INSERT OR IGNORE INTO singles_user_rankings(user_id,real_name, wins, losses, total, ranking, location)
              VALUES(?,?,?,?,?,?,?)"""
    cur = conn.cursor()
    success = cur.execute(sql, singles_ranking)
    if success:
        logger.info("Successfully added new player")
    singles_ranking = Player(
        {
            "user_id": user_id,
            "real_name": real_name,
            "wins": wins,
            "losses": losses,
            "total": total,
            "ranking": ranking,
            "location": channel_id,
        }
    )
    conn.commit()
    return singles_ranking


def full_rankings(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM singles_user_rankings ORDER by ranking DESC")
    results = cur.fetchall()
    if not results:
        return
    full_rankings = []
    for result in results:
        full_rankings.append(
            Player(
                {
                    "user_id": result[1],
                    "real_name": result[2],
                    "wins": result[3],
                    "losses": result[4],
                    "total": result[5],
                    "ranking": result[6],
                    "location": result[7],
                }
            )
        )
    return full_rankings


def location_rankings(conn, location):
    location = ("%" + location + "%",)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM singles_user_rankings where location LIKE ? ORDER by ranking DESC", location,
    )
    results = cur.fetchall()
    if not results:
        return
    location_rankings = []
    for result in results:
        location_rankings.append(
            Player(
                {
                    "user_id": result[1],
                    "real_name": result[2],
                    "wins": result[3],
                    "losses": result[4],
                    "total": result[5],
                    "ranking": result[6],
                    "location": result[7],
                }
            )
        )
    return location_rankings


def full_game_history(conn):
    cur = conn.cursor()
    cur.execute("SELECT * FROM singles_results_table ORDER by game_date ASC")
    results = cur.fetchall()
    if not results:
        return
    game_history = []
    for result in results:
        game_history.append(
            Game(
                {
                    "winner": result[1],
                    "winner_id": result[2],
                    "loser": result[3],
                    "loser_id": result[4],
                    "location": result[5],
                    "game_date": result[6],
                }
            )
        )
    return game_history


def prediction_history(conn, requester_id, opponent_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM singles_results_table WHERE (winner_id = ? AND loser_id = ? OR winner_id = ? AND loser_id = ?) ORDER by game_date ASC",
        (requester_id, opponent_id, opponent_id, requester_id),
    )
    results = cur.fetchall()
    if not results:
        return
    prediction_results = []
    for result in results:
        prediction_results.append(
            Game(
                {
                    "winner": result[1],
                    "winner_id": result[2],
                    "loser": result[3],
                    "loser_id": result[4],
                    "location": result[5],
                    "game_date": result[6],
                }
            )
        )
    return prediction_results
