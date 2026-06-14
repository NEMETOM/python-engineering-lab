from compliance_service.rules.base import Rule
from compliance_service.rules.compliance.duplicate_order import DuplicateOrderRule
from compliance_service.rules.compliance.invalid_symbol import InvalidSymbolRule
from compliance_service.rules.compliance.market_hours import MarketHoursRule
from compliance_service.rules.compliance.missing_client_id import MissingClientIdRule
from compliance_service.rules.compliance.price_deviation import PriceDeviationRule
from compliance_service.rules.compliance.trade_size import TradeSizeRule
from compliance_service.rules.surveillance.rapid_fire import RapidFireRule
from compliance_service.rules.surveillance.repeated_orders import RepeatedOrdersRule
from compliance_service.rules.surveillance.volume_spike import VolumeSpikeRule
from compliance_service.rules.surveillance.wash_trading import WashTradingRule


def build_compliance_rules(policies: dict) -> list[Rule]:
    cfg = policies.get("compliance", {})
    return [
        MissingClientIdRule(cfg.get("missing_client_id", {})),
        MarketHoursRule(cfg.get("market_hours", {})),
        TradeSizeRule(cfg.get("trade_size", {})),
        DuplicateOrderRule(cfg.get("duplicate_order", {})),
        PriceDeviationRule(cfg.get("price_deviation", {})),
        InvalidSymbolRule(cfg.get("allowed_symbols", {})),
    ]


def build_surveillance_rules(policies: dict) -> list[Rule]:
    cfg = policies.get("surveillance", {})
    return [
        WashTradingRule(cfg.get("wash_trading", {})),
        RapidFireRule(cfg.get("rapid_fire", {})),
        VolumeSpikeRule(cfg.get("volume_spike", {})),
        RepeatedOrdersRule(cfg.get("repeated_orders", {})),
    ]
