"""Canonical list of togglable rules: id, category, and display label.

Order within each category must match the instantiation order in
rules/loader.py's build_compliance_rules/build_surveillance_rules - consumer.py
zips this catalog's ids against those instances to build a rule_id -> Rule
registry for live overrides. A length mismatch there raises loudly rather than
silently mis-mapping ids to the wrong rule.
"""

RULE_CATALOG: list[dict[str, str]] = [
    {
        "rule_id": "missing_client_id",
        "category": "compliance",
        "label": "Missing Client ID",
        "description": "Flags any order that arrives without a client identifier.",
    },
    {
        "rule_id": "market_hours",
        "category": "compliance",
        "label": "Market Hours",
        "description": "Flags orders submitted outside configured market hours.",
    },
    {
        "rule_id": "trade_size",
        "category": "compliance",
        "label": "Trade Size",
        "description": "Flags orders whose quantity exceeds the per-symbol or default limit.",
    },
    {
        "rule_id": "duplicate_order",
        "category": "compliance",
        "label": "Duplicate Order",
        "description": "Flags identical orders from the same client within a rolling time window.",
    },
    {
        "rule_id": "price_deviation",
        "category": "compliance",
        "label": "Price Deviation",
        "description": "Flags orders whose price deviates more than a threshold from the rolling average.",
    },
    {
        "rule_id": "allowed_symbols",
        "category": "compliance",
        "label": "Allowed Symbols",
        "description": "Flags orders for instruments not on the approved symbol list.",
    },
    {
        "rule_id": "wash_trading",
        "category": "surveillance",
        "label": "Wash Trading",
        "description": "Detects the same client trading both sides of the same instrument within a window.",
    },
    {
        "rule_id": "rapid_fire",
        "category": "surveillance",
        "label": "Rapid Fire",
        "description": "Detects clients submitting an unusually high number of orders in a short window.",
    },
    {
        "rule_id": "volume_spike",
        "category": "surveillance",
        "label": "Volume Spike",
        "description": "Detects individual orders whose quantity far exceeds the baseline average for that symbol.",
    },
    {
        "rule_id": "repeated_orders",
        "category": "surveillance",
        "label": "Repeated Orders",
        "description": "Detects suspiciously identical orders from the same client within a rolling window.",
    },
]

RULE_IDS: frozenset[str] = frozenset(r["rule_id"] for r in RULE_CATALOG)


def rule_ids_by_category(category: str) -> list[str]:
    return [r["rule_id"] for r in RULE_CATALOG if r["category"] == category]
