# fix-protocol-simulator/tests/test_fix_server.py

from fix_simulator.server.fix_server import FixServer


def test_fix_server_stores_host_and_port():
    server = FixServer("127.0.0.1", 9878)
    assert server.host == "127.0.0.1"
    assert server.port == 9878
