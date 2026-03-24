# fix-protocol-simulator/scripts/run_client.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fix_simulator.utils.logger import setup_logger
from fix_simulator.client.fix_client import FixClient

if __name__ == "__main__":
    setup_logger()

    client = FixClient()
    client.connect()

    client.send_order(symbol="AAPL", price=100.0, quantity=5, side="BUY")

    client.close()
