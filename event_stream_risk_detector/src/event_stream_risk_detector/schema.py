#src/event_stream_risk_detector/schema.py

# Simple example schema
RISK_EVENT_SCHEMA = {
    "transaction_id": str,
    "user_id": str,
    "amount": float,
    "country": str,
    "timestamp": str
}