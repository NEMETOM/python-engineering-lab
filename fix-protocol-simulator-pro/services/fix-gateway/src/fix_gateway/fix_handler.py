# fix-protocol-simulator-pro/services/fix-gateway/src/fix_gateway/fix_handler.py

# now
from fix_gateway.utils.logger import get_logger

# later
# from common_utils.logger import configure_logging, get_logger


logger = get_logger(__name__)


class FixHandler:

    def __init__(self, delimiter="|"):

        self.delimiter = delimiter

    def parse(self, raw_message: str) -> dict:

        fields = raw_message.strip().split(self.delimiter)

        fix_dict = {}

        for field in fields:

            if "=" not in field:

                continue

            tag, value = field.split("=", 1)

            fix_dict[tag] = value

        logger.debug(f"parsed FIX message {fix_dict}")

        return fix_dict

    def is_logon(self, msg: dict):

        return msg.get("35") == "A"

    def is_heartbeat(self, msg: dict):

        return msg.get("35") == "0"

    def is_new_order(self, msg: dict):

        return msg.get("35") == "D"
