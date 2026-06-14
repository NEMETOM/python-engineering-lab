from risk_service.position_store import PositionStore


class TestFreshStore:
    def setup_method(self):
        self.store = PositionStore()

    def test_net_position_starts_at_zero(self):
        assert self.store.get_net_position("C1", "AAPL") == 0

    def test_gross_position_starts_at_zero(self):
        assert self.store.get_gross_position("C1", "AAPL") == 0

    def test_open_order_count_starts_at_zero(self):
        assert self.store.get_open_order_count("C1") == 0


class TestOpenOrders:
    def setup_method(self):
        self.store = PositionStore()

    def test_record_increases_open_count(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        assert self.store.get_open_order_count("C1") == 1

    def test_multiple_records_accumulate(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        self.store.record_open_order("O2", "C1", "AAPL", "SELL", 50)
        assert self.store.get_open_order_count("C1") == 2

    def test_counts_are_per_client(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        self.store.record_open_order("O2", "C2", "AAPL", "BUY", 100)
        assert self.store.get_open_order_count("C1") == 1
        assert self.store.get_open_order_count("C2") == 1

    def test_fill_decreases_open_count(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        self.store.fill_order("O1")
        assert self.store.get_open_order_count("C1") == 0

    def test_fill_unknown_order_is_noop(self):
        self.store.fill_order("NONEXISTENT")
        assert self.store.get_open_order_count("C1") == 0

    def test_fill_unknown_order_does_not_raise(self):
        self.store.fill_order("NONEXISTENT")  # should not raise


class TestPositionTracking:
    def setup_method(self):
        self.store = PositionStore()

    def test_buy_fill_increases_net_position(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 500)
        self.store.fill_order("O1")
        assert self.store.get_net_position("C1", "AAPL") == 500

    def test_sell_fill_decreases_net_position(self):
        self.store.record_open_order("O1", "C1", "AAPL", "SELL", 300)
        self.store.fill_order("O1")
        assert self.store.get_net_position("C1", "AAPL") == -300

    def test_buy_then_sell_nets_to_zero(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        self.store.fill_order("O1")
        self.store.record_open_order("O2", "C1", "AAPL", "SELL", 100)
        self.store.fill_order("O2")
        assert self.store.get_net_position("C1", "AAPL") == 0

    def test_gross_position_is_absolute_of_net(self):
        self.store.record_open_order("O1", "C1", "AAPL", "SELL", 200)
        self.store.fill_order("O1")
        assert self.store.get_net_position("C1", "AAPL") == -200
        assert self.store.get_gross_position("C1", "AAPL") == 200

    def test_positions_are_per_symbol(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        self.store.fill_order("O1")
        assert self.store.get_net_position("C1", "MSFT") == 0

    def test_positions_are_per_client(self):
        self.store.record_open_order("O1", "C1", "AAPL", "BUY", 100)
        self.store.fill_order("O1")
        assert self.store.get_net_position("C2", "AAPL") == 0

    def test_fill_without_record_does_not_corrupt_position(self):
        self.store.fill_order("GHOST")
        assert self.store.get_net_position("C1", "AAPL") == 0
