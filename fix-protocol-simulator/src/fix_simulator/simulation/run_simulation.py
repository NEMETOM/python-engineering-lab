#fix-protocol-simulator/src/fix_simulator/simulation\run_simulation.py

import asyncio

from fix_simulator.server.fix_server import FixServer
from fix_simulator.config.settings import settings
from fix_simulator.utils.logger import setup_logger


def run():

    setup_logger()

    server = FixServer(settings.host, settings.port)

    asyncio.run(server.start())