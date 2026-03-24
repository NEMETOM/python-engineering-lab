# fix-protocol-simulator/tests/test_fix_client.py

from fix_simulator.client.fix_client import FixClient


def test_fix_client_stores_host_and_port():
    client = FixClient("127.0.0.1", 9878)
    assert client.host == "127.0.0.1"
    assert client.port == 9878


def test_fix_client_initial_seq_num_is_zero():
    client = FixClient("127.0.0.1", 9878)
    assert client._seq_num == 0
