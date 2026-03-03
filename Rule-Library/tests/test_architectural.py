"""Tests for architectural rules: cursor patterns (OBQ-040..044) and DDL objects (OBQ-045..050)."""

import pytest


class TestCursorPatterns:
    """OBQ-040..044: PL/SQL cursor and type attribute patterns."""

    def test_cursor_rules_count(self, cursor_rules):
        assert len(cursor_rules) == 5

    def test_for_loop_cursor(self, rules_by_id):
        r = rules_by_id["OBQ-040"]
        assert r["source_pattern"]["construct"] == "CURSOR_FOR_LOOP"
        assert r["severity"] == "critical"
        assert "set-based" in r["target_pattern"].lower()

    def test_bulk_collect(self, rules_by_id):
        r = rules_by_id["OBQ-041"]
        assert r["source_pattern"]["construct"] == "BULK_COLLECT"
        assert r["severity"] == "critical"

    def test_open_fetch_close(self, rules_by_id):
        r = rules_by_id["OBQ-042"]
        assert r["source_pattern"]["construct"] == "OPEN_FETCH_CLOSE"
        assert r["severity"] == "critical"

    def test_rowtype_attribute(self, rules_by_id):
        r = rules_by_id["OBQ-043"]
        assert r["source_pattern"]["construct"] == "ROWTYPE_ATTRIBUTE"
        assert "STRUCT" in r["target_pattern"]

    def test_type_attribute(self, rules_by_id):
        r = rules_by_id["OBQ-044"]
        assert r["source_pattern"]["construct"] == "TYPE_ATTRIBUTE"

    @pytest.mark.parametrize("rule_id", ["OBQ-040", "OBQ-041", "OBQ-042", "OBQ-043", "OBQ-044"])
    def test_each_cursor_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1

    def test_cursor_rules_have_low_confidence(self, cursor_rules):
        """Cursor patterns are hard to automate — confidence should be <= 0.7."""
        for r in cursor_rules:
            assert r["confidence"] <= 0.7, (
                f"Rule {r['rule_id']} confidence {r['confidence']} is too high for a cursor pattern"
            )


class TestDDLObjects:
    """OBQ-045..050: DDL object translation patterns."""

    def test_ddl_rules_count(self, ddl_rules):
        assert len(ddl_rules) == 6

    def test_trigger_to_cloud_functions(self, rules_by_id):
        r = rules_by_id["OBQ-045"]
        assert r["source_pattern"]["object_type"] == "TRIGGER"
        assert r["severity"] == "critical"

    def test_package_to_standalone(self, rules_by_id):
        r = rules_by_id["OBQ-046"]
        assert r["source_pattern"]["object_type"] == "PACKAGE"
        assert r["severity"] == "critical"

    def test_sequence_to_generate_uuid(self, rules_by_id):
        r = rules_by_id["OBQ-047"]
        assert r["source_pattern"]["object_type"] == "SEQUENCE"
        assert "GENERATE_UUID" in r["target_pattern"]

    def test_synonym_to_fqn(self, rules_by_id):
        r = rules_by_id["OBQ-048"]
        assert r["source_pattern"]["object_type"] == "SYNONYM"

    def test_dblink_to_external_query(self, rules_by_id):
        r = rules_by_id["OBQ-049"]
        assert r["source_pattern"]["object_type"] == "DBLINK"
        assert "EXTERNAL_QUERY" in r["target_pattern"]

    def test_exception_block(self, rules_by_id):
        r = rules_by_id["OBQ-050"]
        assert r["source_pattern"]["construct"] == "EXCEPTION_BLOCK"
        assert "EXCEPTION" in r["target_pattern"]

    @pytest.mark.parametrize(
        "rule_id", ["OBQ-045", "OBQ-046", "OBQ-047", "OBQ-048", "OBQ-049", "OBQ-050"]
    )
    def test_each_ddl_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1
