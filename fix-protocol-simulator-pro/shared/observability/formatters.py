import json
import logging
import os

SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown")


class JsonFormatter(logging.Formatter):

    def format(self, record):

        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }

        return json.dumps(log_record)
