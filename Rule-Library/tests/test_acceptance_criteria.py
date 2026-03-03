"""Three critical acceptance tests that must NEVER fail.

1. DECODE NULL  → IF(x IS NULL, r1, r2)  (never CASE WHEN x = NULL)
2. SYSDATE      → CURRENT_DATETIME()     (never CURRENT_DATE())
3. NUMBER       → NUMERIC                (never FLOAT64)
"""

import pytest


class TestDecodeNullGotcha:
    """OBQ-004: DECODE(x, NULL, r1, r2) must output IF(x IS NULL, r1, r2), not CASE WHEN x = NULL."""

    def test_rule_exists(self, rules_by_id):
        assert "OBQ-004" in rules_by_id, "OBQ-004 (DECODE NULL gotcha) missing"

    def test_severity_is_critical(self, rules_by_id):
        assert rules_by_id["OBQ-004"]["severity"] == "critical"

    def test_target_uses_if_is_null(self, rules_by_id):
        target = rules_by_id["OBQ-004"]["target_pattern"]
        assert target.startswith("IF("), (
            f"OBQ-004 target must use IF() form, got: {target}"
        )
        assert "IS NULL" in target, (
            f"OBQ-004 target must use IS NULL, got: {target}"
        )
        assert "= NULL" not in target, (
            f"OBQ-004 target must NOT use = NULL, got: {target}"
        )

    def test_test_cases_use_if_is_null(self, rules_by_id):
        for tc in rules_by_id["OBQ-004"]["tests"]:
            expected = tc["expected"]
            assert expected.startswith("IF("), (
                f"OBQ-004 test expected must use IF() form, got: {expected}"
            )
            assert "IS NULL" in expected, (
                f"OBQ-004 test expected must use IS NULL, got: {expected}"
            )
            assert "= NULL" not in expected, (
                f"OBQ-004 test expected must NOT use = NULL, got: {expected}"
            )


class TestSysdateMapping:
    """OBQ-005: SYSDATE must map to CURRENT_DATETIME(), never CURRENT_DATE()."""

    def test_rule_exists(self, rules_by_id):
        assert "OBQ-005" in rules_by_id, "OBQ-005 (SYSDATE) missing"

    def test_severity_is_critical(self, rules_by_id):
        assert rules_by_id["OBQ-005"]["severity"] == "critical"

    def test_target_is_current_datetime(self, rules_by_id):
        target = rules_by_id["OBQ-005"]["target_pattern"]
        assert "CURRENT_DATETIME()" in target, (
            f"OBQ-005 target must be CURRENT_DATETIME(), got: {target}"
        )

    def test_target_is_not_current_date(self, rules_by_id):
        target = rules_by_id["OBQ-005"]["target_pattern"]
        # CURRENT_DATETIME() contains CURRENT_DATE as a substring, so check exact
        assert target.strip() == "CURRENT_DATETIME()", (
            f"OBQ-005 target must be exactly CURRENT_DATETIME(), got: {target}"
        )

    def test_test_cases_use_current_datetime(self, rules_by_id):
        for tc in rules_by_id["OBQ-005"]["tests"]:
            assert "CURRENT_DATETIME()" in tc["expected"], (
                f"OBQ-005 test expected must use CURRENT_DATETIME(), got: {tc['expected']}"
            )


class TestNumberMapping:
    """OBQ-031: NUMBER must map to NUMERIC, never FLOAT64."""

    def test_rule_exists(self, rules_by_id):
        assert "OBQ-031" in rules_by_id, "OBQ-031 (NUMBER to NUMERIC) missing"

    def test_severity_is_critical(self, rules_by_id):
        assert rules_by_id["OBQ-031"]["severity"] == "critical"

    def test_target_is_numeric(self, rules_by_id):
        target = rules_by_id["OBQ-031"]["target_pattern"]
        assert "NUMERIC" in target, (
            f"OBQ-031 target must be NUMERIC, got: {target}"
        )

    def test_target_is_not_float64(self, rules_by_id):
        target = rules_by_id["OBQ-031"]["target_pattern"]
        assert "FLOAT64" not in target, (
            f"OBQ-031 target must NOT be FLOAT64, got: {target}"
        )

    def test_test_cases_use_numeric(self, rules_by_id):
        for tc in rules_by_id["OBQ-031"]["tests"]:
            assert "NUMERIC" in tc["expected"], (
                f"OBQ-031 test expected must use NUMERIC, got: {tc['expected']}"
            )
            assert "FLOAT64" not in tc["expected"], (
                f"OBQ-031 test expected must NOT use FLOAT64, got: {tc['expected']}"
            )
