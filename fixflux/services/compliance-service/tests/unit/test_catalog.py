from compliance_service.rules.catalog import (
    RULE_CATALOG,
    RULE_IDS,
    rule_ids_by_category,
)


class TestRuleCatalog:
    def test_every_rule_has_a_nonempty_description(self):
        for rule in RULE_CATALOG:
            assert rule.get("description"), f"{rule['rule_id']} has no description"

    def test_rule_ids_are_unique(self):
        ids = [rule["rule_id"] for rule in RULE_CATALOG]
        assert len(ids) == len(set(ids))

    def test_rule_ids_match_frozenset(self):
        assert RULE_IDS == {rule["rule_id"] for rule in RULE_CATALOG}

    def test_categories_partition_the_catalog(self):
        compliance_ids = rule_ids_by_category("compliance")
        surveillance_ids = rule_ids_by_category("surveillance")
        assert len(compliance_ids) + len(surveillance_ids) == len(RULE_CATALOG)
