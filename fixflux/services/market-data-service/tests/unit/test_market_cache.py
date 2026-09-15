from market_data_service.market_cache import MarketCache


def test_trade_updates_price_for_its_symbol():

    cache = MarketCache()

    cache.update_trade({"symbol": "AAPL", "price": 100})

    snapshot = cache.snapshot()

    assert snapshot["AAPL"]["last_trade_price"] == 100


def test_order_book_update_stores_best_bid_and_ask_for_its_symbol():

    cache = MarketCache()

    cache.update_order_book({"symbol": "AAPL", "best_bid": 99.50, "best_ask": 100.50})

    snapshot = cache.snapshot()

    assert snapshot["AAPL"]["best_bid"] == 99.50
    assert snapshot["AAPL"]["best_ask"] == 100.50


def test_snapshot_includes_symbol_and_mid_price():

    cache = MarketCache()

    cache.update_order_book({"symbol": "AAPL", "best_bid": 99.50, "best_ask": 100.50})

    snapshot = cache.snapshot()["AAPL"]

    assert snapshot["symbol"] == "AAPL"
    assert snapshot["mid_price"] == 100.0


def test_symbols_are_tracked_independently():

    cache = MarketCache()

    cache.update_trade({"symbol": "AAPL", "price": 100})
    cache.update_trade({"symbol": "BTCUSD", "price": 50000})
    cache.update_order_book({"symbol": "AAPL", "best_bid": 99.0, "best_ask": 101.0})

    snapshot = cache.snapshot()

    assert snapshot["AAPL"]["last_trade_price"] == 100
    assert snapshot["AAPL"]["best_bid"] == 99.0
    assert snapshot["BTCUSD"]["last_trade_price"] == 50000
    assert snapshot["BTCUSD"]["best_bid"] is None


def test_updates_missing_symbol_are_ignored():

    cache = MarketCache()

    cache.update_trade({"price": 100})
    cache.update_order_book({"best_bid": 99.0, "best_ask": 101.0})

    assert cache.snapshot() == {}


def test_empty_cache_has_no_entries():

    cache = MarketCache()

    assert cache.snapshot() == {}
