import sys
import logging
import logging.config
from setup_logging import logger
from slackbot.bot import Bot


def main():
    kw = {
        "format": "[%(asctime)s] %(levelname)s: %(message)s",
        "datefmt": "%m/%d/%Y %H:%M:%S",
        "level": logging.INFO,
        "stream": sys.stdout,
    }
    logging.basicConfig(**kw)

    bot = Bot()
    bot.run()


if __name__ == "__main__":

    main()
