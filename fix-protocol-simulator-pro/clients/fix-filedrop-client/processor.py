import shutil
from datetime import datetime, timezone

from config import PROCESSED_DIR, REJECTED_DIR
from fix_gateway.fix_handler import FixHandler
from logger import get_logger
from shared.infrastructure.kafka_client import create_producer
from shared.observability.metrics import (
    fix_messages_parse_errors,
    fix_messages_received,
    fix_sessions_active,
)
from validator import validate_fix

logger = get_logger(__name__)

_DEAD_LETTER_TOPIC = "dead_letter_orders"


class FileProcessor:
    def __init__(self):
        self.producer = create_producer()
        self.handler = FixHandler()

    def process(self, filepath):
        try:
            with open(filepath, "r") as f:
                lines = [line.strip() for line in f if line.strip()]

            success, skipped = 0, 0

            for raw in lines:
                try:
                    msg = self.handler.parse(raw)
                    msg_type = msg.get("35", "")

                    if msg_type == "A":
                        fix_sessions_active.inc()
                        fix_messages_received.labels(msg_type="logon").inc()
                        success += 1
                        continue

                    validate_fix(msg)

                    event = {
                        "symbol": msg["55"],
                        "side": "BUY" if msg["54"] == "1" else "SELL",
                        "price": float(msg["44"]),
                        "quantity": int(msg["38"]),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    self.producer.send("raw_orders", event)
                    fix_messages_received.labels(msg_type="new_order").inc()
                    success += 1

                except Exception as e:
                    fix_messages_parse_errors.inc()
                    skipped += 1
                    logger.warning(f"skipped line in {filepath.name}: {e}")
                    self.producer.send(
                        _DEAD_LETTER_TOPIC,
                        {
                            "source_file": filepath.name,
                            "raw_line": raw,
                            "error": str(e),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

            shutil.move(filepath, PROCESSED_DIR / filepath.name)
            logger.info(
                f"processed {filepath.name}: {success} published, {skipped} skipped"
            )

        except Exception as e:
            shutil.move(filepath, REJECTED_DIR / filepath.name)
            logger.error(f"rejected file {filepath.name} reason={e}")
            self.producer.send(
                _DEAD_LETTER_TOPIC,
                {
                    "source_file": filepath.name,
                    "raw_line": None,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
