"""Tests for direct swap rules: null handling, datetime, string, set & misc."""

import pytest


class TestNullHandling:
    """OBQ-001..004: Null handling function swaps."""

    def test_null_handling_count(self, null_handling_rules):
        assert len(null_handling_rules) == 4

    def test_nvl_maps_to_ifnull(self, rules_by_id):
        r = rules_by_id["OBQ-001"]
        assert r["source_pattern"]["function"] == "NVL"
        assert "IFNULL" in r["target_pattern"]
        assert r["confidence"] == 1.0

    def test_nvl2_maps_to_if_is_not_null(self, rules_by_id):
        r = rules_by_id["OBQ-002"]
        assert r["source_pattern"]["function"] == "NVL2"
        assert "IS NOT NULL" in r["target_pattern"]

    def test_decode_maps_to_case_when(self, rules_by_id):
        r = rules_by_id["OBQ-003"]
        assert r["source_pattern"]["function"] == "DECODE"
        assert "CASE WHEN" in r["target_pattern"]

    def test_decode_null_is_critical(self, rules_by_id):
        r = rules_by_id["OBQ-004"]
        assert r["severity"] == "critical"
        assert r["source_pattern"]["arg_type"] == "null_compare"

    @pytest.mark.parametrize("rule_id", ["OBQ-001", "OBQ-002", "OBQ-003", "OBQ-004"])
    def test_each_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1


class TestDatetime:
    """OBQ-005..012: Datetime function swaps."""

    def test_datetime_count(self, datetime_rules):
        assert len(datetime_rules) == 8

    def test_sysdate_to_current_datetime(self, rules_by_id):
        r = rules_by_id["OBQ-005"]
        assert r["source_pattern"]["keyword"] == "SYSDATE"
        assert r["target_pattern"] == "CURRENT_DATETIME()"
        assert r["severity"] == "critical"

    def test_trunc_sysdate_to_current_date(self, rules_by_id):
        r = rules_by_id["OBQ-006"]
        assert r["source_pattern"]["function"] == "TRUNC"
        assert "CURRENT_DATE()" in r["target_pattern"]

    def test_add_months_to_date_add(self, rules_by_id):
        r = rules_by_id["OBQ-007"]
        assert r["source_pattern"]["function"] == "ADD_MONTHS"
        assert "DATE_ADD" in r["target_pattern"]
        assert "INTERVAL" in r["target_pattern"]

    def test_months_between_to_date_diff(self, rules_by_id):
        r = rules_by_id["OBQ-008"]
        assert r["source_pattern"]["function"] == "MONTHS_BETWEEN"
        assert "DATE_DIFF" in r["target_pattern"]

    def test_to_char_date_to_format_datetime(self, rules_by_id):
        r = rules_by_id["OBQ-009"]
        assert r["source_pattern"]["function"] == "TO_CHAR"
        assert "FORMAT_DATETIME" in r["target_pattern"]

    def test_to_date_to_parse_datetime(self, rules_by_id):
        r = rules_by_id["OBQ-010"]
        assert r["source_pattern"]["function"] == "TO_DATE"
        assert "PARSE_DATETIME" in r["target_pattern"]

    def test_systimestamp_to_current_timestamp(self, rules_by_id):
        r = rules_by_id["OBQ-011"]
        assert r["source_pattern"]["keyword"] == "SYSTIMESTAMP"
        assert "CURRENT_TIMESTAMP()" in r["target_pattern"]

    def test_to_timestamp_to_parse_timestamp(self, rules_by_id):
        r = rules_by_id["OBQ-012"]
        assert r["source_pattern"]["function"] == "TO_TIMESTAMP"
        assert "PARSE_TIMESTAMP" in r["target_pattern"]

    @pytest.mark.parametrize(
        "rule_id",
        ["OBQ-005", "OBQ-006", "OBQ-007", "OBQ-008", "OBQ-009", "OBQ-010", "OBQ-011", "OBQ-012"],
    )
    def test_each_datetime_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1


class TestStringFunctions:
    """OBQ-013..017: String function swaps."""

    def test_string_count(self, string_rules):
        assert len(string_rules) == 5

    def test_instr_to_strpos(self, rules_by_id):
        r = rules_by_id["OBQ-013"]
        assert r["source_pattern"]["function"] == "INSTR"
        assert "STRPOS" in r["target_pattern"]

    def test_lengthb_to_byte_length(self, rules_by_id):
        r = rules_by_id["OBQ-014"]
        assert r["source_pattern"]["function"] == "LENGTHB"
        assert "BYTE_LENGTH" in r["target_pattern"]

    def test_listagg_to_string_agg(self, rules_by_id):
        r = rules_by_id["OBQ-015"]
        assert r["source_pattern"]["function"] == "LISTAGG"
        assert "STRING_AGG" in r["target_pattern"]

    def test_substr_compatible(self, rules_by_id):
        r = rules_by_id["OBQ-016"]
        assert r["source_pattern"]["function"] == "SUBSTR"
        assert r["confidence"] == 1.0

    def test_double_pipe_to_concat(self, rules_by_id):
        r = rules_by_id["OBQ-017"]
        assert r["source_pattern"]["construct"] == "DOUBLE_PIPE_CONCAT"
        assert "CONCAT" in r["target_pattern"]


class TestSetAndMisc:
    """OBQ-018..022: Set operations and miscellaneous."""

    def test_set_and_misc_count(self, set_and_misc_rules):
        assert len(set_and_misc_rules) == 5

    def test_minus_to_except_distinct(self, rules_by_id):
        r = rules_by_id["OBQ-018"]
        assert r["source_pattern"]["keyword"] == "MINUS"
        assert "EXCEPT DISTINCT" in r["target_pattern"]

    def test_dual_removal(self, rules_by_id):
        r = rules_by_id["OBQ-019"]
        assert r["source_pattern"]["keyword"] == "FROM_DUAL"

    def test_rownum_where_to_limit(self, rules_by_id):
        r = rules_by_id["OBQ-020"]
        assert r["source_pattern"]["construct"] == "ROWNUM_WHERE"
        assert "LIMIT" in r["target_pattern"]

    def test_rownum_select_to_row_number(self, rules_by_id):
        r = rules_by_id["OBQ-021"]
        assert r["source_pattern"]["construct"] == "ROWNUM_SELECT"
        assert "ROW_NUMBER()" in r["target_pattern"]

    def test_regexp_like_to_regexp_contains(self, rules_by_id):
        r = rules_by_id["OBQ-022"]
        assert r["source_pattern"]["function"] == "REGEXP_LIKE"
        assert "REGEXP_CONTAINS" in r["target_pattern"]
