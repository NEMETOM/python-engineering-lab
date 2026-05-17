# fix-protocol-simulator-pro/services/fix-gateway/tests/unit/test_server.py

from unittest.mock import MagicMock, patch

from fix_gateway.server import FixServer


def test_server_init():

    server = FixServer()

    assert server.host == "0.0.0.0"
    assert server.port == 9878
    assert server.session_manager is not None
    assert server.fix_handler is not None


def test_process_message_logon():

    server = FixServer()
    fix_msg = {"35": "A", "49": "CLIENT1"}

    server.process_message(fix_msg)

    assert server.session_manager.get_session("CLIENT1") is not None


def test_process_message_heartbeat():

    server = FixServer()
    server.session_manager.create_session("CLIENT1")

    fix_msg = {"35": "0", "49": "CLIENT1"}
    server.process_message(fix_msg)

    assert server.session_manager.get_session("CLIENT1") is not None


def test_process_message_new_order():

    server = FixServer()
    fix_msg = {"35": "D", "49": "CLIENT1", "55": "BTCUSD", "54": "1", "44": "50000"}

    server.process_message(fix_msg)  # should not raise


def test_process_message_unknown_type_does_not_raise():

    server = FixServer()
    fix_msg = {"35": "Z", "49": "CLIENT1"}

    server.process_message(fix_msg)  # should not raise


def test_handle_connection_reads_and_processes():

    server = FixServer()

    raw = b"35=A|49=CLIENT1|"
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.side_effect = [raw, b""]

    server.handle_connection(conn)

    assert server.session_manager.get_session("CLIENT1") is not None


def test_handle_connection_empty_data_exits_loop():

    server = FixServer()

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.return_value = b""

    server.handle_connection(conn)  # should exit cleanly without processing
