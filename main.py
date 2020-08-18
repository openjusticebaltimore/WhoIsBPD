import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ResponseBot'))
from responsebot.responsebot import ResponseBot

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'BPDWatch'))
from OpenOversight.app import app


if __name__ == '__main__':
    app.app_context().push()
    bot = ResponseBot(handlers_package=os.path.join(os.path.dirname(__file__), 'handlers'))
    bot.start()