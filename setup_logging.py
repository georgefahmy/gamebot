from datetime import datetime
import re, json, sys, os
import logging
from logging.handlers import TimedRotatingFileHandler


def initLogger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    fh = TimedRotatingFileHandler("logs/pong.log", when="midnight", interval=1)
    fh.setLevel(logging.DEBUG)
    fh.suffix = "%Y%m%d"
    formatter1 = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %H:%M:%S"
    )
    fh.setFormatter(formatter1)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter2 = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %H:%M:%S"
    )
    ch.setFormatter(formatter2)
    logger.addHandler(ch)
    return logger


logger = initLogger()
