from unittest.mock import MagicMock

from fix_replay.parser import ReplayOrder
from fix_replay.replayer import Replayer


def _order(client="C1", side="BUY"):
    return ReplayOrder("f:1", client, "AAPL", side, 175.5, 100)


class TestReplayer:
    def test_sends_raw_order_shape_with_namespaced_client(self):
        producer = MagicMock()
        Replayer(producer, "RPL-x-", rate=0).send([_order()])

        topic, event = producer.send.call_args.args
        assert topic == "raw_orders"
        assert event["client_id"] == "RPL-x-C1"
        assert {k: event[k] for k in ("symbol", "side", "price", "quantity")} == {
            "symbol": "AAPL",
            "side": "BUY",
            "price": 175.5,
            "quantity": 100,
        }
        assert isinstance(event["timestamp"], str)

    def test_preserves_order_and_flushes(self):
        producer = MagicMock()
        sent = Replayer(producer, "P-", rate=0).send([_order("A"), _order("B", "SELL")])
        assert sent == 2
        clients = [c.args[1]["client_id"] for c in producer.send.call_args_list]
        assert clients == ["P-A", "P-B"]
        producer.flush.assert_called_once()

    def test_throttles_between_orders_not_before_first(self):
        sleep = MagicMock()
        Replayer(MagicMock(), "P-", rate=4, sleep=sleep).send([_order()] * 3)
        assert [c.args[0] for c in sleep.call_args_list] == [0.25, 0.25]

    def test_rate_zero_never_sleeps(self):
        sleep = MagicMock()
        Replayer(MagicMock(), "P-", rate=0, sleep=sleep).send([_order()] * 3)
        sleep.assert_not_called()
