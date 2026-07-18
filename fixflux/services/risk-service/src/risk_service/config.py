import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

NOTIONAL_LIMIT = float(os.getenv("RISK_NOTIONAL_LIMIT", "1000000"))
FAT_FINGER_PCT = float(os.getenv("RISK_FAT_FINGER_PCT", "10.0"))
GROSS_POSITION_LIMIT = int(os.getenv("RISK_GROSS_POSITION_LIMIT", "10000"))
NET_POSITION_LIMIT = int(os.getenv("RISK_NET_POSITION_LIMIT", "5000"))
MAX_OPEN_ORDERS = int(os.getenv("RISK_MAX_OPEN_ORDERS", "10"))

INPUT_TOPIC = "validated_orders"
APPROVED_TOPIC = "risk_approved_orders"
REJECTED_TOPIC = "risk_rejected_orders"
TRADES_TOPIC = "trades"
EXEC_REPORTS_TOPIC = "execution_reports"
GROUP_ID = "risk-service"
