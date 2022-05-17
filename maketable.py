#!/usr/bin/env python3.7
import sqlite3
from sqlite3 import Error
import os, sys

# This creates the database file in the working directory
file = "pongbot_v2.db"
if not os.path.exists(file):
    with open(file, "w"):
        pass


def create_connection(file):
    # create a database connection to the SQLite database
    # specified by db_file
    conn = None
    try:
        conn = sqlite3.connect(file)
        return conn
    except Error as e:
        print(e)

    return conn


def create_table(conn, create_table_sql):
    # create a table from the create_table_sql statement
    # :param conn: Connection object
    # :param create_table_sql: a CREATE TABLE statement
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def main():

    create_singles_results_table = """CREATE TABLE singles_results_table (
                                    	id integer PRIMARY KEY,
                                    	winner text NOT NULL,
                                    	winner_id text NOT NULL,
                                    	loser text NOT NULL,
                                    	loser_id text NOT NULL,
                                        location text NOT NULL,
                                    	game_date datetime NOT NULL
    );"""

    create_singles_rankings_table = """ CREATE TABLE IF NOT EXISTS singles_user_rankings (
                                        id integer PRIMARY KEY,
                                        user_id text NOT NULL UNIQUE,
                                        real_name text NOT NULL,
                                        wins int NOT NULL,
                                        losses int NOT NULL,
                                        total int NOT NULL,
                                        ranking int NOT NULL
    );"""

    create_doubles_results_table = """CREATE TABLE doubles_results_table (
                                        id integer PRIMARY KEY,
                                        winning_team text NOT NULL,
                                        winning_team_ids text NOT NULL,
                                    	losing_team text NOT NULL,
                                    	losing_team_ids text NOT NULL,
                                        location text NOT NULL,
                                    	game_date datetime NOT NULL
    );"""

    create_doubles_rankings_table = """CREATE TABLE doubles_rankings_table (
                                        id integer PRIMARY KEY,
                                        player_1 text NOT NULL,
                                        player_1_id text NOT NULL,
                                    	player_2 text NOT NULL,
                                    	player_2_id text NOT NULL,
                                    	team_name text NOT NULL,
                                    	team_name_ids text NOT NULL UNIQUE,
                                        wins int NOT NULL,
                                        losses int NOT NULL,
                                        total int NOT NULL,
                                        ranking int NOT NULL
    );"""
    create_logs_table = """CREATE TABLE log_messages (
                                        id integer PRIMARY KEY,
                                        requester_id text NOT NULL,
                                        requester_real_name text NOT NULL,
                                        channel_id text NOT NULL,
                                        channel_name text NOT NULL,
                                        log_message text NOT NULL,
                                        message_date text NOT NULL,
                                        slack_link text NOT NULL
    );"""

    # create a database connection
    conn = create_connection(file)

    # create tables
    if conn is not None:
        # create projects table
        create_table(conn, create_singles_results_table)
        create_table(conn, create_singles_rankings_table)
        create_table(conn, create_doubles_results_table)
        create_table(conn, create_doubles_rankings_table)
        create_table(conn, create_logs_table)

    else:
        print("Error! cannot create the database connection.")


if __name__ == "__main__":
    main()
