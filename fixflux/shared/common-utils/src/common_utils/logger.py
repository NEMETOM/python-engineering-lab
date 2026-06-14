# fixflux/shared/common-utils/src/common_util/logger.py

import logging
import sys


def configure_logging():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name):

    return logging.getLogger(name)
