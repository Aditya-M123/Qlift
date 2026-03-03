"""Tests for shared BigQuery rules SBQ-001..005."""

import pytest


class TestSharedBigQuery:
    """Validate all 5 shared BigQuery pattern rules."""

    def test_shared_count(self, bigquery_rules):
        assert len(bigquery_rules) == 5

    def test_partition_recommendation(self, rules_by_id):
        r = rules_by_id["SBQ-001"]
        assert "PARTITION BY" in r["target_pattern"]
        assert "optimization" in r["tags"]

    def test_safe_divide(self, rules_by_id):
        r = rules_by_id["SBQ-002"]
        assert "SAFE_DIVIDE" in r["target_pattern"]
        assert r["confidence"] == 0.9

    def test_is_null_pattern(self, rules_by_id):
        r = rules_by_id["SBQ-003"]
        assert "IS NULL" in r["target_pattern"]
        assert r["confidence"] == 1.0

    def test_generate_uuid(self, rules_by_id):
        r = rules_by_id["SBQ-004"]
        assert "GENERATE_UUID()" in r["target_pattern"]

    def test_clustering_recommendation(self, rules_by_id):
        r = rules_by_id["SBQ-005"]
        assert "CLUSTER BY" in r["target_pattern"]
        assert "optimization" in r["tags"]

    @pytest.mark.parametrize(
        "rule_id", ["SBQ-001", "SBQ-002", "SBQ-003", "SBQ-004", "SBQ-005"]
    )
    def test_each_shared_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1

    def test_all_shared_rules_have_bigquery_tag(self, bigquery_rules):
        for r in bigquery_rules:
            assert "bigquery" in r["tags"], (
                f"Rule {r['rule_id']} should have 'bigquery' tag"
            )
