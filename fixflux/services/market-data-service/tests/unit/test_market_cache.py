from market_data_service.market_cache import MarketCache


def test_trade_updates_price():

    cache = MarketCache()

    cache.update_trade({"price": 100})

    snapshot = cache.snapshot()

    assert snapshot["last_trade_price"] == 100


def test_order_book_update_stores_best_bid_and_ask():

    cache = MarketCache()

    cache.update_order_book({"best_bid": 99.50, "best_ask": 100.50})

    snapshot = cache.snapshot()

    assert snapshot["best_bid"] == 99.50
    assert snapshot["best_ask"] == 100.50


def test_initial_snapshot_fields_are_none():

    cache = MarketCache()

    snapshot = cache.snapshot()

    assert snapshot["last_trade_price"] is None
    assert snapshot["best_bid"] is None
    assert snapshot["best_ask"] is None
