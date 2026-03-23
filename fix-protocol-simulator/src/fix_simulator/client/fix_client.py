#fix-protocol-simulator/src/fix_simulator/client/fix_client.py

import socket
import logging
import uuid

from fix_simulator.protocol.fix_message import FixMessage
from fix_simulator.protocol.fix_parser import FixParser
from fix_simulator.protocol.fix_constants import (
    MSG_TYPE, SENDER_COMP_ID, TARGET_COMP_ID, MSG_SEQ_NUM,
    NEW_ORDER_SINGLE,
)
from fix_simulator.config.settings import settings

logger = logging.getLogger(__name__)


class FixClient:

    def __init__(self, host=settings.host, port=settings.port):
        self.host = host
        self.port = port
        self._seq_num = 0

    def connect(self):
        self.socket = socket.socket()
        self.socket.connect((self.host, self.port))
        logger.info(f"Connected to exchange {self.host}:{self.port}")

    def close(self):
        self.socket.close()
        logger.info("Disconnected from exchange")

    def send_order(self, symbol: str, price: float, quantity: int, side: str):
        self._seq_num += 1
        msg = FixMessage(fields={
            MSG_TYPE: NEW_ORDER_SINGLE,
            SENDER_COMP_ID: settings.target_comp_id,
            TARGET_COMP_ID: settings.sender_comp_id,
            MSG_SEQ_NUM: str(self._seq_num),
            "55": symbol,
            "44": str(price),
            "38": str(quantity),
            "54": "1" if side.upper() == "BUY" else "2",
            "11": str(uuid.uuid4()),
        })
        raw = FixParser.serialize(msg)
        self.socket.send(raw.encode())
        logger.info(f"Sent NewOrderSingle symbol={symbol} side={side} price={price} qty={quantity}")

    def receive(self):
        data = self.socket.recv(4096).decode()
        logger.info(f"Received {data}")
        return FixParser.parse(data)
