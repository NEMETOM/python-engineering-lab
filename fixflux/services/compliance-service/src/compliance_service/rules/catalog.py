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
    },
    {"rule_id": "market_hours", "category": "compliance", "label": "Market Hours"},
    {"rule_id": "trade_size", "category": "compliance", "label": "Trade Size"},
    {
        "rule_id": "duplicate_order",
        "category": "compliance",
        "label": "Duplicate Order",
    },
    {
        "rule_id": "price_deviation",
        "category": "compliance",
        "label": "Price Deviation",
    },
    {
        "rule_id": "allowed_symbols",
        "category": "compliance",
        "label": "Allowed Symbols",
    },
    {"rule_id": "wash_trading", "category": "surveillance", "label": "Wash Trading"},
    {"rule_id": "rapid_fire", "category": "surveillance", "label": "Rapid Fire"},
    {"rule_id": "volume_spike", "category": "surveillance", "label": "Volume Spike"},
    {
        "rule_id": "repeated_orders",
        "category": "surveillance",
        "label": "Repeated Orders",
    },
]

RULE_IDS: frozenset[str] = frozenset(r["rule_id"] for r in RULE_CATALOG)


def rule_ids_by_category(category: str) -> list[str]:
    return [r["rule_id"] for r in RULE_CATALOG if r["category"] == category]
