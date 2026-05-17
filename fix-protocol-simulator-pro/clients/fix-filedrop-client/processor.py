import shutil
from datetime import datetime

from config import PROCESSED_DIR, REJECTED_DIR
from fix_gateway.fix_handler import FixHandler  # reuse your existing parser
from logger import get_logger
from shared.infrastructure.kafka_client import create_producer
from validator import validate_fix

logger = get_logger(__name__)


class FileProcessor:

    def __init__(self):

        self.producer = create_producer()
        self.handler = FixHandler()

    def process(self, filepath):

        try:

            with open(filepath, "r") as f:
                raw = f.read()

            msg = self.handler.parse(raw)

            validate_fix(msg)

            event = {
                "symbol": msg["55"],
                "side": "BUY" if msg["54"] == "1" else "SELL",
                "price": float(msg["44"]),
                "quantity": int(msg["38"]),
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.producer.send("raw_orders", event)

            shutil.move(filepath, PROCESSED_DIR / filepath.name)

            logger.info(f"processed file {filepath.name}")

        except Exception as e:

            shutil.move(filepath, REJECTED_DIR / filepath.name)

            logger.error(f"rejected file {filepath.name} reason={e}")
