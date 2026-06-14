from datetime import datetime
from unittest.mock import MagicMock, patch

import trade_store.consumer  # noqa: F401  # ensure module is in sys.modules before @patch decorators fire


def _msg_value(**overrides):
    defaults = dict(
        trade_id="T001",
        symbol="AAPL",
        buy_order_id="B001",
        sell_order_id="S001",
        price=150.0,
        quantity=10,
        timestamp=datetime.utcnow().isoformat(),
    )
    return {**defaults, **overrides}


def _make_msg(**overrides):
    msg = MagicMock()
    msg.value = _msg_value(**overrides)
    return msg


class TestConsumerSubscription:
    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_subscribes_to_trades_topic_with_correct_group(
        self, mock_create, _mock_repo
    ):
        mock_create.return_value = iter([])
        from trade_store.consumer import run

        run()
        mock_create.assert_called_once_with("trades", "trade-store")


class TestConsumerProcessing:
    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_valid_message_is_saved(self, mock_create, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_create.return_value = iter([_make_msg()])
        from trade_store.consumer import run

        run()
        mock_repo.save.assert_called_once()

    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_multiple_messages_each_saved(self, mock_create, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_create.return_value = iter([_make_msg() for _ in range(3)])
        from trade_store.consumer import run

        run()
        assert mock_repo.save.call_count == 3

    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_no_messages_does_not_save(self, mock_create, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_create.return_value = iter([])
        from trade_store.consumer import run

        run()
        mock_repo.save.assert_not_called()


class TestConsumerErrorHandling:
    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_bad_data_does_not_crash(self, mock_create, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        bad_msg = MagicMock()
        bad_msg.value = {"not": "a trade"}
        mock_create.return_value = iter([bad_msg])
        from trade_store.consumer import run

        run()  # must not raise

    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_repo_failure_does_not_crash(self, mock_create, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo.save.side_effect = Exception("DB down")
        mock_repo_cls.return_value = mock_repo
        mock_create.return_value = iter([_make_msg()])
        from trade_store.consumer import run

        run()  # must not raise

    @patch("trade_store.consumer.TradeRepository")
    @patch("trade_store.consumer.create_consumer")
    def test_bad_message_does_not_block_next(self, mock_create, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        bad_msg = MagicMock()
        bad_msg.value = {"garbage": True}
        good_msg = _make_msg()
        mock_create.return_value = iter([bad_msg, good_msg])
        from trade_store.consumer import run

        run()
        mock_repo.save.assert_called_once()
