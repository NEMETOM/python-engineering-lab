# fixflux/services/fix-gateway/tests/unit/test_server.py

from unittest.mock import MagicMock

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


def test_process_message_logon_returns_sender():
    server = FixServer()
    fix_msg = {"35": "A", "49": "CLIENT1"}

    result = server.process_message(fix_msg)

    assert result == ("CLIENT1", False)


def test_process_message_non_logon_returns_none_sender_and_not_closed():
    server = FixServer()

    assert server.process_message({"35": "0", "49": "CLIENT1"}) == (None, False)
    assert server.process_message({"35": "D", "49": "CLIENT1"}) == (None, False)
    assert server.process_message({"35": "Z", "49": "CLIENT1"}) == (None, False)


def test_process_message_logout_returns_sender_and_closes():
    server = FixServer()
    server.session_manager.create_session("CLIENT1")

    result = server.process_message({"35": "5", "49": "CLIENT1"})

    assert result == ("CLIENT1", True)


def test_process_message_new_order_counts_as_heartbeat_activity():
    server = FixServer()
    server.session_manager.create_session("CLIENT1")
    session = server.session_manager.get_session("CLIENT1")
    stale_time = session.last_heartbeat.replace(year=2000)
    session.last_heartbeat = stale_time

    server.process_message(
        {"35": "D", "49": "CLIENT1", "55": "BTCUSD", "54": "1", "44": "50000"}
    )

    assert server.session_manager.get_session("CLIENT1").last_heartbeat != stale_time


def test_handle_connection_reads_and_processes():
    server = FixServer()

    raw = b"35=A|49=CLIENT1|"
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.side_effect = [raw, b""]

    server.handle_connection(conn)

    # session is created during logon then removed on TCP close
    assert server.session_manager.get_session("CLIENT1") is None


def test_handle_connection_removes_session_on_disconnect():
    server = FixServer()

    logon = b"35=A|49=CLIENT2|"
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.side_effect = [logon, b""]

    server.handle_connection(conn)

    assert server.session_manager.get_session("CLIENT2") is None


def test_handle_connection_empty_data_exits_loop():
    server = FixServer()

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.return_value = b""

    server.handle_connection(conn)  # no logon, no session to remove


def test_handle_connection_logout_closes_connection_without_waiting_for_tcp_close():
    server = FixServer()

    logon = b"35=A|49=CLIENT3|"
    logout = b"35=5|49=CLIENT3|"
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.side_effect = [logon, logout, b""]

    server.handle_connection(conn)

    assert server.session_manager.get_session("CLIENT3") is None
    # Logout should break the loop immediately - the trailing b"" in side_effect
    # is there only to prove the test would catch it if logout handling failed
    # to stop the loop (call_count would then be 3).
    assert conn.recv.call_count == 2


def test_handle_connection_heartbeat_timeout_expires_session():
    server = FixServer()

    logon = b"35=A|49=CLIENT4|"
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.side_effect = [logon, TimeoutError()]
    # Don't sleep in a test to produce a real stale timestamp - the thing under
    # test is handle_connection's wiring to SessionManager.is_expired, not
    # SessionManager's own elapsed-time arithmetic (covered separately in
    # test_session_manager.py).
    server.session_manager.is_expired = MagicMock(return_value=True)

    server.handle_connection(conn)

    assert server.session_manager.get_session("CLIENT4") is None


def test_handle_connection_timeout_before_logon_keeps_waiting():
    server = FixServer()

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.side_effect = [TimeoutError(), TimeoutError(), b""]

    server.handle_connection(conn)  # should not raise; no session to clean up

    assert conn.recv.call_count == 3


def test_handle_connection_sets_socket_timeout_to_heartbeat_timeout():
    server = FixServer()

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.recv.return_value = b""

    server.handle_connection(conn)

    conn.settimeout.assert_called_once_with(server.heartbeat_timeout)
