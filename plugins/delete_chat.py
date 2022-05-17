#!/usr/bin/env python3.7
from slackbot.bot import respond_to, listen_to
from slackbot_settings import API_TOKEN, USER_TOKEN
from setup_logging import logger
import re, json, sys, os
import slack
import logging

sc = slack.WebClient(token=API_TOKEN, ssl=False)
user_sc = slack.WebClient(token=USER_TOKEN, ssl=False)


def delete_bot_chat(timestamp, channel):
    try:
        sc.chat_delete(channel=channel, ts=timestamp)
        return True
    except:
        return False


def delete_user_chat(timestamp, channel):
    try:
        user_sc.chat_delete(channel=channel, ts=timestamp)
        return True
    except:
        return False


def timestamp_channel_extractor(link):
    link = link.strip("<").strip(">")
    link_split = link.split("/")
    for i in link_split:
        if i.startswith("p"):
            try:
                i = i.split("?")[0]
                timestamp = str(i[1:-6] + "." + i[-6:])
                logger.info("Timestamp: %s", timestamp)
            except:
                timestamp = str(i[1:-6] + "." + i[-6:])
                logger.info("Timestamp: %s", timestamp)
        if i.startswith("C") or i.startswith("G"):
            logger.info("Channel: %s", i)
            channel = i

    return timestamp, channel


@listen_to("^gb delete (.*)", re.IGNORECASE)
@listen_to("^pong delete (.*)", re.IGNORECASE)
def delete_chat(message, link):
    logger.info("Link: %s", link)

    delete_message_ts = message._body["event_ts"]
    delete_message_channel = message.channel._body["id"]
    logger.info(
        "Delete message request channel: %s and timestamp: %s",
        delete_message_channel,
        delete_message_ts,
    )
    links = link.split()
    logger.info("Links: %s", links)
    for link in links:
        timestamp, channel = timestamp_channel_extractor(link)

        deleted = delete_bot_chat(timestamp, channel)
        logger.info("Deleted bot message: %s", deleted)

    if deleted:
        message.react("check")
        success = delete_user_chat(delete_message_ts, delete_message_channel)
        logger.info("Deleted user message: %s", success)
    else:
        message.react("exclamation")
