# fix-protocol-simulator-pro/services/fix-gateway/src/fix_gateway/server.py

import socket

from prometheus_client import start_http_server

from fix_gateway.config import settings
from fix_gateway.fix_handler import FixHandler
from fix_gateway.session_manager import SessionManager
from fix_gateway.utils.logger import configure_logging, get_logger
from shared.observability.metrics import (
    fix_messages_parse_errors,
    fix_messages_received,
    fix_reconnect_attempts,
)

configure_logging()

logger = get_logger(__name__)

_METRICS_PORT = 8001


class FixServer:
    def __init__(self):
        self.host = settings.host
        self.port = settings.port
        self.session_manager = SessionManager()
        self.fix_handler = FixHandler(delimiter=settings.fix_delimiter)

    def start(self):
        logger.info(f"starting FIX server {self.host}:{self.port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind((self.host, self.port))
            server.listen()
            while True:
                conn, addr = server.accept()
                logger.info(f"client connected {addr}")
                self.handle_connection(conn)

    def handle_connection(self, conn):
        sender = None
        with conn:
            while True:
                data = conn.recv(settings.buffer_size)
                if not data:
                    break
                raw_message = data.decode()
                logger.debug(f"received raw FIX {raw_message}")
                fix_msg = self.fix_handler.parse(raw_message)
                sender = self.process_message(fix_msg) or sender
        if sender:
            self.session_manager.remove_session(sender)
            logger.info(f"client disconnected {sender}")

    def process_message(self, fix_msg: dict) -> str | None:
        if self.fix_handler.is_logon(fix_msg):
            sender = fix_msg.get("49")
            if self.session_manager.get_session(sender):
                fix_reconnect_attempts.inc()
            self.session_manager.create_session(sender)
            fix_messages_received.labels(msg_type="logon").inc()
            logger.info("logon processed")
            return sender
        elif self.fix_handler.is_heartbeat(fix_msg):
            sender = fix_msg.get("49")
            self.session_manager.update_heartbeat(sender)
            fix_messages_received.labels(msg_type="heartbeat").inc()
            logger.debug("heartbeat processed")
        elif self.fix_handler.is_new_order(fix_msg):
            fix_messages_received.labels(msg_type="new_order").inc()
            logger.info("new order received")
            logger.debug(fix_msg)
        else:
            fix_messages_parse_errors.inc()
            logger.warning(
                f"unrecognized FIX message type: {fix_msg.get('35', 'none')}"
            )
        return None


if __name__ == "__main__":
    start_http_server(_METRICS_PORT)
    logger.info(f"metrics server started on :{_METRICS_PORT}")
    server = FixServer()
    server.start()
