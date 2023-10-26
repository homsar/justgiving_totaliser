import logging
import sys

from .justgiving_totaliser import main

debug = False
if len(sys.argv) > 0 and sys.argv[1] == "debug":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    debug = True

main(debug)
