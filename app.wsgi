import os
import sys

APP_PATH = os.path.dirname(__file__)

os.chdir(APP_PATH)
sys.path.append(APP_PATH)

import bottle
import main
main.setup()
application = bottle.default_app()
