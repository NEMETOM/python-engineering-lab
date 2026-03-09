# price-calculator/tests/test_risk_evaluator.py

from event_stream_risk_detector.risk_evaluator import evaluate_transaction


def test_low_value_transaction() -> None:
    tx = {"transaction_id": "1", "user_id": "u1", "amount": 100}

    result = evaluate_transaction(tx)

    assert result["high_value"] is False


def test_high_value_transaction() -> None:
    tx = {"transaction_id": "2", "user_id": "u1", "amount": 20000}

    result = evaluate_transaction(tx)

    assert result["high_value"] is True
