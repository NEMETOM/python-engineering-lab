#fix-protocol-simulator/src/fix_simulator/protocol/fix_parser.py

import logging
from .fix_message import FixMessage
from .fix_constants import SOH

logger = logging.getLogger(__name__)

class FixParser:
    @staticmethod
    def parse(raw_message: str) -> FixMessage:
        logger.info("Parsing FIX message")

        fields = {}

        parts = raw_message.split(SOH)

        for part in parts:
            if "=" in part:
                tag, value = part.split("=", 1)
                fields[tag] = value

        return FixMessage(fields)

    @staticmethod
    def serialize(message: FixMessage) -> str:

        logger.debug("Serializing FIX message")

        return message.encode()      

