import logging
import json
import uuid


def get_logger():
    logger = logging.getLogger("compliance")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()

    correlation_id = str(uuid.uuid4())

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "level": record.levelname,
                "message": record.getMessage(),
                "correlation_id": correlation_id,
            }
            return json.dumps(log_record)

    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    return logger
