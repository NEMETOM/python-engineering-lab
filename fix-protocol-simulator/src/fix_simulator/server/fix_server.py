#fix-protocol-simulator/src/fix_simulator/server/fix_server.py

import asyncio
import logging

from fix_simulator.protocol.fix_parser import FixParser

logger = logging.getLogger(__name__)


class FixServer:

    def __init__(self, host, port):

        self.host = host
        self.port = port

    async def handle_client(self, reader, writer):

        addr = writer.get_extra_info("peername")

        logger.info(f"Client connected {addr}")

        while True:

            data = await reader.read(4096)

            if not data:
                break

            message = data.decode()

            logger.info(f"Received {message}")

            fix_message = FixParser.parse(message)

            logger.info(f"Parsed message {fix_message.fields}")

        writer.close()

    async def start(self):

        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        logger.info(f"FIX server running {self.host}:{self.port}")

        async with server:
            await server.serve_forever()