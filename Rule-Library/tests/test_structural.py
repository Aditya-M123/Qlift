"""Tests for structural pattern rules OBQ-051..056."""

import pytest


class TestStructuralPatterns:
    """Validate all 6 structural translation patterns."""

    def test_structural_count(self, structural_rules):
        assert len(structural_rules) == 6

    def test_connect_by_to_recursive_cte(self, rules_by_id):
        r = rules_by_id["OBQ-051"]
        assert r["source_pattern"]["construct"] == "CONNECT_BY_PRIOR"
        assert r["severity"] == "critical"
        assert "RECURSIVE" in r["target_pattern"]

    def test_start_with_to_cte_anchor(self, rules_by_id):
        r = rules_by_id["OBQ-052"]
        assert r["source_pattern"]["construct"] == "START_WITH"
        assert "anchor" in r["target_pattern"].lower()

    def test_lateral_to_cross_join_unnest(self, rules_by_id):
        r = rules_by_id["OBQ-053"]
        assert r["source_pattern"]["construct"] == "LATERAL_VIEW"
        assert "CROSS JOIN UNNEST" in r["target_pattern"]

    def test_pivot_compatible(self, rules_by_id):
        r = rules_by_id["OBQ-054"]
        assert r["source_pattern"]["construct"] == "PIVOT"
        assert "PIVOT" in r["target_pattern"]
        assert r["confidence"] == 0.9

    def test_merge_compatible(self, rules_by_id):
        r = rules_by_id["OBQ-055"]
        assert r["source_pattern"]["construct"] == "MERGE"
        assert "MERGE" in r["target_pattern"]
        assert r["confidence"] == 0.95

    def test_outer_join_syntax(self, rules_by_id):
        r = rules_by_id["OBQ-056"]
        assert r["source_pattern"]["construct"] == "ORACLE_OUTER_JOIN"
        assert "LEFT OUTER JOIN" in r["target_pattern"]

    @pytest.mark.parametrize(
        "rule_id", ["OBQ-051", "OBQ-052", "OBQ-053", "OBQ-054", "OBQ-055", "OBQ-056"]
    )
    def test_each_structural_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1

    def test_hierarchical_rules_are_critical_or_high(self, rules_by_id):
        """CONNECT BY and START WITH are complex patterns requiring careful review."""
        for rid in ["OBQ-051", "OBQ-052"]:
            assert rules_by_id[rid]["severity"] in {"critical", "high"}
