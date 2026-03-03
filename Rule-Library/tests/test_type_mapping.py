"""Tests for type mapping rules OBQ-030..039."""

import pytest


class TestTypeMapping:
    """Validate all 10 Oracle-to-BigQuery type mappings."""

    def test_type_mapping_count(self, type_mapping_rules):
        assert len(type_mapping_rules) == 10

    def test_varchar2_to_string(self, rules_by_id):
        r = rules_by_id["OBQ-030"]
        assert r["source_pattern"]["object_type"] == "VARCHAR2"
        assert r["target_pattern"] == "STRING"

    def test_number_to_numeric(self, rules_by_id):
        r = rules_by_id["OBQ-031"]
        assert r["source_pattern"]["object_type"] == "NUMBER"
        assert r["target_pattern"] == "NUMERIC"
        assert r["severity"] == "critical"

    def test_number_int_to_int64(self, rules_by_id):
        r = rules_by_id["OBQ-032"]
        assert r["source_pattern"]["object_type"] == "NUMBER_INT"
        assert r["target_pattern"] == "INT64"

    def test_clob_to_string(self, rules_by_id):
        r = rules_by_id["OBQ-033"]
        assert r["source_pattern"]["object_type"] == "CLOB"
        assert r["target_pattern"] == "STRING"

    def test_blob_to_bytes(self, rules_by_id):
        r = rules_by_id["OBQ-034"]
        assert r["source_pattern"]["object_type"] == "BLOB"
        assert r["target_pattern"] == "BYTES"

    def test_xmltype_to_json(self, rules_by_id):
        r = rules_by_id["OBQ-035"]
        assert r["source_pattern"]["object_type"] == "XMLTYPE"
        assert r["target_pattern"] == "JSON"
        assert r["confidence"] == 0.7
        assert "lossy" in r["tags"]

    def test_date_to_datetime(self, rules_by_id):
        r = rules_by_id["OBQ-036"]
        assert r["source_pattern"]["object_type"] == "DATE"
        assert r["target_pattern"] == "DATETIME"

    def test_timestamp_compatible(self, rules_by_id):
        r = rules_by_id["OBQ-037"]
        assert r["source_pattern"]["object_type"] == "TIMESTAMP"
        assert r["target_pattern"] == "TIMESTAMP"
        assert r["confidence"] == 1.0

    def test_char_to_string(self, rules_by_id):
        r = rules_by_id["OBQ-038"]
        assert r["source_pattern"]["object_type"] == "CHAR"
        assert r["target_pattern"] == "STRING"

    def test_raw_to_bytes(self, rules_by_id):
        r = rules_by_id["OBQ-039"]
        assert r["source_pattern"]["object_type"] == "RAW"
        assert r["target_pattern"] == "BYTES"

    @pytest.mark.parametrize(
        "rule_id",
        ["OBQ-030", "OBQ-031", "OBQ-032", "OBQ-033", "OBQ-034",
         "OBQ-035", "OBQ-036", "OBQ-037", "OBQ-038", "OBQ-039"],
    )
    def test_each_type_rule_has_tests(self, rules_by_id, rule_id):
        assert len(rules_by_id[rule_id]["tests"]) >= 1

    def test_number_never_maps_to_float64(self, rules_by_id):
        """Critical: NUMBER must NEVER map to FLOAT64."""
        r = rules_by_id["OBQ-031"]
        assert "FLOAT64" not in r["target_pattern"]
        for tc in r["tests"]:
            assert "FLOAT64" not in tc["expected"]
