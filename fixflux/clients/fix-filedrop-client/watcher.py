import time
from pathlib import Path

from config import FILEDROP_DIR
from logger import get_logger
from processor import FileProcessor
from prometheus_client import start_http_server

logger = get_logger(__name__)

_METRICS_PORT = 8005


def run():

    start_http_server(_METRICS_PORT)

    logger.info(f"metrics server started on :{_METRICS_PORT}")

    processor = FileProcessor()

    seen = set()

    while True:

        for file in Path(FILEDROP_DIR).glob("*.txt"):

            if file not in seen:

                logger.info(f"new file detected {file.name}")

                processor.process(file)

                seen.add(file)

        time.sleep(2)


if __name__ == "__main__":

    run()
