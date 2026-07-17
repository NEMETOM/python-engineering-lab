from prometheus_client import Counter, Gauge, Histogram

# FIX Gateway
fix_messages_received = Counter(
    "fix_messages_received_total",
    "FIX messages received by the gateway",
    ["msg_type"],
)
fix_messages_parse_errors = Counter(
    "fix_messages_parse_errors_total",
    "FIX messages with unrecognized or missing message type",
)
fix_sessions_active = Gauge(
    "fix_sessions_active",
    "Currently active FIX sessions",
)
fix_reconnect_attempts = Counter(
    "fix_reconnect_attempts_total",
    "FIX client reconnection attempts (logon from existing session)",
)

# Matching Engine
trades_executed = Counter(
    "trades_executed_total",
    "Trades executed by the matching engine",
    ["symbol"],
)
order_matching_latency = Histogram(
    "order_matching_latency_seconds",
    "Time to process an order through the matching engine",
    buckets=[0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
)
orders_in_book = Gauge(
    "orders_in_book",
    "Orders currently resting in the order book",
    ["side", "symbol"],
)

# Order Processing
orders_processed = Counter(
    "orders_processed_total",
    "Orders processed by the order service",
    ["status"],  # approved, rejected
)

# Compliance Service
violations_detected = Counter(
    "violations_detected_total",
    "Compliance rule violations detected",
    ["rule", "severity"],
)

# Kafka
kafka_messages_consumed = Counter(
    "kafka_messages_consumed_total",
    "Kafka messages consumed",
    ["topic", "service"],
)
kafka_messages_produced = Counter(
    "kafka_messages_produced_total",
    "Kafka messages produced",
    ["topic", "service"],
)

# Trade Store
trades_stored = Counter(
    "trades_stored_total",
    "Trades persisted to storage",
    ["symbol"],
)
api_requests = Counter(
    "api_requests_total",
    "HTTP requests to the trade store API",
    ["endpoint", "method", "status_code"],
)
api_request_latency = Histogram(
    "api_request_latency_seconds",
    "HTTP API request latency",
    ["endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
