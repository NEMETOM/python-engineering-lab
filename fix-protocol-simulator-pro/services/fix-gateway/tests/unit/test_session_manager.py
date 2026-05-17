# fix-protocol-simulator-pro/services/fix-gateway/tests/unit/test_session_manager.py

import time

from fix_gateway.session_manager import SessionManager


def test_create_session():

    manager = SessionManager()

    session = manager.create_session("CLIENT1")

    assert session.sender_comp_id == "CLIENT1"
    assert session.session_id is not None
    assert session.created_at is not None


def test_get_existing_session():

    manager = SessionManager()
    manager.create_session("CLIENT1")

    session = manager.get_session("CLIENT1")

    assert session is not None
    assert session.sender_comp_id == "CLIENT1"


def test_get_unknown_session_returns_none():

    manager = SessionManager()

    assert manager.get_session("UNKNOWN") is None


def test_create_session_overwrites_existing():

    manager = SessionManager()

    first = manager.create_session("CLIENT1")
    second = manager.create_session("CLIENT1")

    assert manager.get_session("CLIENT1").session_id == second.session_id
    assert first.session_id != second.session_id


def test_update_heartbeat():

    manager = SessionManager()
    manager.create_session("CLIENT1")

    before = manager.get_session("CLIENT1").last_heartbeat
    time.sleep(0.01)
    manager.update_heartbeat("CLIENT1")
    after = manager.get_session("CLIENT1").last_heartbeat

    assert after > before


def test_update_heartbeat_unknown_sender_does_not_raise():

    manager = SessionManager()

    manager.update_heartbeat("UNKNOWN")  # should not raise


def test_multiple_sessions_are_independent():

    manager = SessionManager()
    manager.create_session("CLIENT1")
    manager.create_session("CLIENT2")

    assert manager.get_session("CLIENT1").sender_comp_id == "CLIENT1"
    assert manager.get_session("CLIENT2").sender_comp_id == "CLIENT2"
    assert (
        manager.get_session("CLIENT1").session_id
        != manager.get_session("CLIENT2").session_id
    )
