"""Page objects for the FixFlux Console UI tests.

Every locator lives here, one class per tab. Step definitions call these and
keep the assertions (expect(...)) themselves.
"""

from pages.compliance_rules_page import ComplianceRulesPage, RuleCard
from pages.console import ConsoleNav, ConsolePage
from pages.injector_page import InjectorPage
from pages.market_data_page import MarketDataPage, QuoteRow

__all__ = [
    "ComplianceRulesPage",
    "ConsoleNav",
    "ConsolePage",
    "InjectorPage",
    "MarketDataPage",
    "QuoteRow",
    "RuleCard",
]
