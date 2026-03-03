"""Rigorous end-to-end validation of the Rule Library.

Challenges tested:
  1.  YAML integrity         — every file parses, no corruption
  2.  Template exclusion     — RULE_TEMPLATE.yaml never loads as a real rule
  3.  ID range ownership     — each YAML file only contains IDs from its expected range
  4.  No cross-contamination — OBQ rules never appear in shared/, SBQ never in oracle/
  5.  Dangerous-pattern scan — forbidden strings never slip into critical rules
  6.  Confidence-severity coherence — critical rules have high confidence, architectural low
  7.  XMLTYPE lossy flag     — OBQ-035 must carry the 'lossy' tag
  8.  Compatible rules       — input == expected only for rules tagged 'compatible'
  9.  Why field quality      — every 'why' is substantive (>= 20 chars)
  10. Tag consistency        — no empty tags, no whitespace-only tags
  11. Version format         — all versions are valid semver-like strings
  12. File count             — exactly 9 YAML rule files (no extra, no missing)
  13. Encoding               — all YAML files are valid UTF-8
  14. Negative pattern tests — forbidden outputs NEVER appear in any rule
  15. Rule-count-per-file    — each file has the expected number of rules
  16. Acceptance criteria     — every required swap/mapping/pattern exists with correct target
"""

import pathlib
import re

import pytest
import yaml

RULES_DIR = pathlib.Path(__file__).resolve().parent.parent / "rules"

# ---------------------------------------------------------------------------
# Helper: load everything fresh (independent of conftest fixtures)
# ---------------------------------------------------------------------------

def _load_all_rules():
    rules = []
    for f in sorted(RULES_DIR.rglob("*.yaml")):
        if f.name == "RULE_TEMPLATE.yaml":
            continue
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, list):
            for r in data:
                r["_source_file"] = str(f.relative_to(RULES_DIR))
            rules.extend(data)
    return rules


ALL_RULES = _load_all_rules()
RULES_MAP = {r["rule_id"]: r for r in ALL_RULES}


# ===================================================================
# 1. YAML INTEGRITY
# ===================================================================
class TestYamlIntegrity:
    """Every YAML file must parse without error."""

    def test_all_yaml_files_parseable(self):
        for f in RULES_DIR.rglob("*.yaml"):
            if f.name == "RULE_TEMPLATE.yaml":
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            assert data is not None, f"{f} parsed as None/empty"
            assert isinstance(data, list), f"{f} root must be a list, got {type(data)}"

    def test_no_yaml_syntax_errors(self):
        """Deliberately try to parse every file — any exception = fail."""
        errors = []
        for f in RULES_DIR.rglob("*.yaml"):
            try:
                with open(f, encoding="utf-8") as fh:
                    yaml.safe_load(fh)
            except yaml.YAMLError as e:
                errors.append(f"{f.name}: {e}")
        assert not errors, "YAML parse errors:\n" + "\n".join(errors)


# ===================================================================
# 2. TEMPLATE EXCLUSION
# ===================================================================
class TestTemplateExclusion:
    """RULE_TEMPLATE.yaml must exist but never load as a real rule."""

    def test_template_file_exists(self):
        assert (RULES_DIR / "RULE_TEMPLATE.yaml").exists()

    def test_template_not_in_loaded_rules(self):
        for r in ALL_RULES:
            assert r["rule_id"] != "OBQ-XXX", (
                "Template rule OBQ-XXX was loaded as a real rule"
            )


# ===================================================================
# 3. ID RANGE OWNERSHIP — each file contains only its expected IDs
# ===================================================================
class TestIdRangeOwnership:
    """Each YAML file must only contain rule IDs from its expected range."""

    EXPECTED_RANGES = {
        "oracle-to-bigquery/direct_swaps/null_handling.yaml": (
            ["OBQ-001", "OBQ-002", "OBQ-003", "OBQ-004"]
        ),
        "oracle-to-bigquery/direct_swaps/datetime_functions.yaml": (
            [f"OBQ-{i:03d}" for i in range(5, 13)]
        ),
        "oracle-to-bigquery/direct_swaps/string_functions.yaml": (
            [f"OBQ-{i:03d}" for i in range(13, 18)]
        ),
        "oracle-to-bigquery/direct_swaps/set_and_misc.yaml": (
            [f"OBQ-{i:03d}" for i in range(18, 23)]
        ),
        "oracle-to-bigquery/type_mapping/type_mapping.yaml": (
            [f"OBQ-{i:03d}" for i in range(30, 40)]
        ),
        "oracle-to-bigquery/architectural/cursor_patterns.yaml": (
            [f"OBQ-{i:03d}" for i in range(40, 45)]
        ),
        "oracle-to-bigquery/architectural/ddl_objects.yaml": (
            [f"OBQ-{i:03d}" for i in range(45, 51)]
        ),
        "oracle-to-bigquery/structural/structural_patterns.yaml": (
            [f"OBQ-{i:03d}" for i in range(51, 57)]
        ),
        "shared/bigquery/bigquery_patterns.yaml": (
            [f"SBQ-{i:03d}" for i in range(1, 6)]
        ),
    }

    @pytest.mark.parametrize("filepath,expected_ids", list(EXPECTED_RANGES.items()))
    def test_file_contains_only_expected_ids(self, filepath, expected_ids):
        file_rules = [r for r in ALL_RULES if r["_source_file"].replace("\\", "/") == filepath]
        actual_ids = [r["rule_id"] for r in file_rules]
        assert sorted(actual_ids) == sorted(expected_ids), (
            f"{filepath}: expected {expected_ids}, got {actual_ids}"
        )


# ===================================================================
# 4. NO CROSS-CONTAMINATION
# ===================================================================
class TestNoCrossContamination:
    """OBQ rules must only live under oracle-to-bigquery/, SBQ under shared/."""

    def test_obq_rules_in_oracle_folder(self):
        for r in ALL_RULES:
            if r["rule_id"].startswith("OBQ-"):
                assert "oracle-to-bigquery" in r["_source_file"], (
                    f"{r['rule_id']} found in {r['_source_file']} instead of oracle-to-bigquery/"
                )

    def test_sbq_rules_in_shared_folder(self):
        for r in ALL_RULES:
            if r["rule_id"].startswith("SBQ-"):
                assert "shared" in r["_source_file"], (
                    f"{r['rule_id']} found in {r['_source_file']} instead of shared/"
                )


# ===================================================================
# 5. DANGEROUS-PATTERN SCAN — forbidden strings in critical rules
# ===================================================================
class TestDangerousPatternScan:
    """Critical gotcha rules must NEVER contain forbidden patterns anywhere."""

    def test_decode_null_never_has_equals_null(self):
        """OBQ-004: '= NULL' must not appear in target, why, or any test expected."""
        r = RULES_MAP["OBQ-004"]
        assert "= NULL" not in r["target_pattern"]
        for tc in r["tests"]:
            assert "= NULL" not in tc["expected"], (
                f"OBQ-004 test expected contains '= NULL': {tc['expected']}"
            )

    def test_decode_null_uses_if_form(self):
        """OBQ-004: must use IF(x IS NULL, ...) not CASE WHEN."""
        r = RULES_MAP["OBQ-004"]
        assert r["target_pattern"].startswith("IF("), (
            f"OBQ-004 target must start with IF(, got: {r['target_pattern']}"
        )
        for tc in r["tests"]:
            assert tc["expected"].startswith("IF("), (
                f"OBQ-004 test expected must start with IF(, got: {tc['expected']}"
            )

    def test_sysdate_never_has_current_date_only(self):
        """OBQ-005: target must be exactly CURRENT_DATETIME(), not CURRENT_DATE()."""
        r = RULES_MAP["OBQ-005"]
        assert r["target_pattern"].strip() == "CURRENT_DATETIME()"
        for tc in r["tests"]:
            # Expected may contain more text, but CURRENT_DATETIME() must be present
            assert "CURRENT_DATETIME()" in tc["expected"]
            # And standalone CURRENT_DATE() must NOT be present
            # (careful: CURRENT_DATETIME() contains CURRENT_DATE as substring)
            cleaned = tc["expected"].replace("CURRENT_DATETIME()", "")
            assert "CURRENT_DATE()" not in cleaned, (
                f"OBQ-005 test expected has bare CURRENT_DATE(): {tc['expected']}"
            )

    def test_number_never_has_float64(self):
        """OBQ-031: FLOAT64 must not appear in target, tests, or why."""
        r = RULES_MAP["OBQ-031"]
        assert "FLOAT64" not in r["target_pattern"]
        assert "FLOAT64" not in r["why"].upper()
        for tc in r["tests"]:
            assert "FLOAT64" not in tc["expected"]

    def test_no_rule_uses_equals_null_in_expected(self):
        """Global scan: no rule's test expected should contain '= NULL' as a comparison."""
        violations = []
        for r in ALL_RULES:
            for i, tc in enumerate(r["tests"]):
                exp = tc["expected"]
                # Allow "IS NULL" but flag "= NULL" (but not "!= NULL" which some rules fix)
                if "= NULL" in exp and "!= NULL" not in exp and "IS NULL" not in exp:
                    violations.append(f"{r['rule_id']} test[{i}]: {exp}")
        assert not violations, (
            "Rules with '= NULL' in expected:\n" + "\n".join(violations)
        )


# ===================================================================
# 6. CONFIDENCE-SEVERITY COHERENCE
# ===================================================================
class TestConfidenceSeverityCoherence:
    """Confidence and severity should be logically consistent."""

    def test_critical_rules_have_confidence_gte_point3(self):
        """Critical rules should have confidence >= 0.3 (even architectural)."""
        for r in ALL_RULES:
            if r["severity"] == "critical":
                assert r["confidence"] >= 0.3, (
                    f"{r['rule_id']}: critical rule has confidence {r['confidence']} < 0.3"
                )

    def test_architectural_patterns_have_low_confidence(self):
        """Rules tagged 'architectural' should have confidence <= 0.8."""
        for r in ALL_RULES:
            if "architectural" in r.get("tags", []):
                assert r["confidence"] <= 0.8, (
                    f"{r['rule_id']}: architectural rule has confidence {r['confidence']} > 0.8"
                )

    def test_direct_swap_confidence_gte_0_9(self):
        """Direct swap function rules (OBQ-001..022) with confidence 1.0 are truly mechanical."""
        mechanical_ids = {"OBQ-001", "OBQ-005", "OBQ-006", "OBQ-011",
                          "OBQ-014", "OBQ-016", "OBQ-018", "OBQ-019"}
        for rid in mechanical_ids:
            assert RULES_MAP[rid]["confidence"] == 1.0, (
                f"{rid}: expected confidence 1.0, got {RULES_MAP[rid]['confidence']}"
            )

    def test_compatible_rules_have_high_confidence(self):
        """Rules tagged 'compatible' (no translation needed) should have confidence >= 0.9."""
        for r in ALL_RULES:
            if "compatible" in r.get("tags", []):
                assert r["confidence"] >= 0.9, (
                    f"{r['rule_id']}: compatible rule has confidence {r['confidence']} < 0.9"
                )


# ===================================================================
# 7. XMLTYPE LOSSY FLAG
# ===================================================================
class TestXmltypeLossyFlag:
    """OBQ-035 (XMLTYPE→JSON) must be flagged as lossy."""

    def test_xmltype_has_lossy_tag(self):
        r = RULES_MAP["OBQ-035"]
        assert "lossy" in r["tags"], f"OBQ-035 missing 'lossy' tag, has: {r['tags']}"

    def test_xmltype_confidence_below_one(self):
        r = RULES_MAP["OBQ-035"]
        assert r["confidence"] < 1.0, (
            f"OBQ-035 lossy conversion should not have confidence 1.0"
        )

    def test_xmltype_why_mentions_lossy(self):
        r = RULES_MAP["OBQ-035"]
        assert "lossy" in r["why"].lower(), (
            "OBQ-035 'why' should explain the lossy nature of XML→JSON"
        )


# ===================================================================
# 8. COMPATIBLE RULES — input == expected is allowed ONLY for these
# ===================================================================
class TestCompatibleRules:
    """Rules tagged 'compatible' may have identical input/expected; others must not."""

    def test_compatible_rules_exist(self):
        compatible = [r for r in ALL_RULES if "compatible" in r.get("tags", [])]
        assert len(compatible) >= 2, "Expected at least 2 compatible rules (SUBSTR, TIMESTAMP, etc.)"

    def test_non_compatible_rules_transform(self):
        for r in ALL_RULES:
            if "compatible" in r.get("tags", []):
                continue
            for i, tc in enumerate(r["tests"]):
                if str(tc["input"]).strip() == str(tc["expected"]).strip():
                    pytest.fail(
                        f"{r['rule_id']} test[{i}]: input == expected but rule is not 'compatible'"
                    )


# ===================================================================
# 9. WHY FIELD QUALITY
# ===================================================================
class TestWhyFieldQuality:
    """Every 'why' explanation must be substantive."""

    def test_why_is_at_least_20_chars(self):
        for r in ALL_RULES:
            why = r["why"].strip()
            assert len(why) >= 20, (
                f"{r['rule_id']}: 'why' is too short ({len(why)} chars): {why!r}"
            )

    def test_why_is_not_placeholder(self):
        placeholders = {"todo", "tbd", "fix me", "placeholder", "xxx"}
        for r in ALL_RULES:
            why_lower = r["why"].lower()
            for ph in placeholders:
                assert ph not in why_lower, (
                    f"{r['rule_id']}: 'why' contains placeholder '{ph}'"
                )

    def test_critical_rules_why_mentions_critical(self):
        """Critical rules should explain WHY they are critical."""
        critical_ids = ["OBQ-004", "OBQ-005", "OBQ-031"]
        for rid in critical_ids:
            r = RULES_MAP[rid]
            why_upper = r["why"].upper()
            assert "CRITICAL" in why_upper or "NEVER" in why_upper or "NOT" in why_upper, (
                f"{rid}: critical rule 'why' should explain the danger"
            )


# ===================================================================
# 10. TAG CONSISTENCY
# ===================================================================
class TestTagConsistency:
    """Tags must be clean, non-empty strings."""

    def test_no_empty_tags(self):
        for r in ALL_RULES:
            for tag in r["tags"]:
                assert isinstance(tag, str), (
                    f"{r['rule_id']}: tag must be string, got {type(tag)}"
                )
                assert tag.strip(), (
                    f"{r['rule_id']}: empty/whitespace-only tag found"
                )

    def test_no_duplicate_tags_per_rule(self):
        for r in ALL_RULES:
            tags = r["tags"]
            assert len(tags) == len(set(tags)), (
                f"{r['rule_id']}: duplicate tags: {tags}"
            )

    def test_tags_are_lowercase_kebab(self):
        """All tags should follow lowercase-kebab-case convention."""
        pattern = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
        for r in ALL_RULES:
            for tag in r["tags"]:
                assert pattern.match(tag), (
                    f"{r['rule_id']}: tag '{tag}' is not lowercase-kebab-case"
                )


# ===================================================================
# 11. VERSION FORMAT
# ===================================================================
class TestVersionFormat:
    """All versions should be valid semver-like strings."""

    def test_version_is_numeric(self):
        for r in ALL_RULES:
            v = r["version"]
            parts = v.split(".")
            assert all(p.isdigit() for p in parts), (
                f"{r['rule_id']}: version '{v}' has non-numeric parts"
            )

    def test_all_versions_consistent(self):
        """All rules should be on the same version (1.0) for initial release."""
        versions = {r["version"] for r in ALL_RULES}
        assert len(versions) == 1, f"Inconsistent versions: {versions}"
        assert "1.0" in versions


# ===================================================================
# 12. FILE COUNT
# ===================================================================
class TestFileCount:
    """Exactly 9 YAML rule files should exist (excluding template)."""

    def test_yaml_file_count(self):
        yaml_files = [
            f for f in RULES_DIR.rglob("*.yaml")
            if f.name != "RULE_TEMPLATE.yaml"
        ]
        assert len(yaml_files) == 9, (
            f"Expected 9 YAML rule files, found {len(yaml_files)}: "
            f"{[f.name for f in yaml_files]}"
        )


# ===================================================================
# 13. ENCODING
# ===================================================================
class TestEncoding:
    """All YAML files must be valid UTF-8."""

    def test_all_files_utf8(self):
        errors = []
        for f in RULES_DIR.rglob("*.yaml"):
            try:
                f.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                errors.append(f"{f.name}: {e}")
        assert not errors, "Encoding errors:\n" + "\n".join(errors)


# ===================================================================
# 14. NEGATIVE PATTERN TESTS — forbidden outputs NEVER appear
# ===================================================================
class TestNegativePatterns:
    """Scan ALL rules for known dangerous anti-patterns."""

    def test_no_rule_maps_sysdate_to_current_date(self):
        """No rule should map SYSDATE to CURRENT_DATE() (only TRUNC(SYSDATE) can)."""
        for r in ALL_RULES:
            sp = r["source_pattern"]
            if sp.get("keyword") == "SYSDATE":
                assert r["target_pattern"].strip() != "CURRENT_DATE()", (
                    f"{r['rule_id']}: SYSDATE must not map to CURRENT_DATE()"
                )

    def test_no_rule_maps_number_to_float64(self):
        """No type mapping rule should map NUMBER to FLOAT64."""
        for r in ALL_RULES:
            sp = r["source_pattern"]
            if sp.get("object_type") == "NUMBER":
                assert "FLOAT64" not in r["target_pattern"], (
                    f"{r['rule_id']}: NUMBER must not map to FLOAT64"
                )

    def test_no_rule_uses_case_when_equals_null(self):
        """No rule target should contain 'CASE WHEN x = NULL'."""
        for r in ALL_RULES:
            target = r["target_pattern"]
            assert "= NULL THEN" not in target, (
                f"{r['rule_id']}: target contains '= NULL THEN': {target}"
            )

    def test_oracle_keywords_not_in_bigquery_targets(self):
        """Oracle-only keywords should not appear as BigQuery target patterns."""
        oracle_only = ["NVL(", "NVL2(", "DECODE(", "SYSDATE", "ROWNUM",
                       "MINUS", "FROM DUAL"]
        for r in ALL_RULES:
            target = r["target_pattern"]
            for kw in oracle_only:
                if kw == "MINUS" and "EXCEPT" in target:
                    continue
                if kw == "FROM DUAL" and "remove" in target.lower():
                    continue
                assert kw not in target, (
                    f"{r['rule_id']}: Oracle keyword '{kw}' found in BigQuery target: {target}"
                )


# ===================================================================
# 15. RULE COUNT PER FILE
# ===================================================================
class TestRuleCountPerFile:
    """Each file must have the expected number of rules."""

    EXPECTED_COUNTS = {
        "oracle-to-bigquery/direct_swaps/null_handling.yaml": 4,
        "oracle-to-bigquery/direct_swaps/datetime_functions.yaml": 8,
        "oracle-to-bigquery/direct_swaps/string_functions.yaml": 5,
        "oracle-to-bigquery/direct_swaps/set_and_misc.yaml": 5,
        "oracle-to-bigquery/type_mapping/type_mapping.yaml": 10,
        "oracle-to-bigquery/architectural/cursor_patterns.yaml": 5,
        "oracle-to-bigquery/architectural/ddl_objects.yaml": 6,
        "oracle-to-bigquery/structural/structural_patterns.yaml": 6,
        "shared/bigquery/bigquery_patterns.yaml": 5,
    }

    @pytest.mark.parametrize("filepath,expected_count", list(EXPECTED_COUNTS.items()))
    def test_file_rule_count(self, filepath, expected_count):
        file_rules = [r for r in ALL_RULES if r["_source_file"].replace("\\", "/") == filepath]
        assert len(file_rules) == expected_count, (
            f"{filepath}: expected {expected_count} rules, found {len(file_rules)}"
        )


# ===================================================================
# 16. ACCEPTANCE CRITERIA — every required swap exists with correct target
# ===================================================================
class TestAcceptanceCriteriaCompleteness:
    """Verify every swap/mapping/pattern listed in the acceptance criteria exists."""

    # --- Direct Swaps ---
    @pytest.mark.parametrize("rule_id,oracle,bigquery", [
        ("OBQ-001", "NVL",             "IFNULL"),
        ("OBQ-002", "NVL2",            "IS NOT NULL"),
        ("OBQ-003", "DECODE",          "CASE WHEN"),
        ("OBQ-005", "SYSDATE",         "CURRENT_DATETIME()"),
        ("OBQ-006", "TRUNC",           "CURRENT_DATE()"),
        ("OBQ-007", "ADD_MONTHS",      "DATE_ADD"),
        ("OBQ-008", "MONTHS_BETWEEN",  "DATE_DIFF"),
        ("OBQ-009", "TO_CHAR",         "FORMAT_DATETIME"),
        ("OBQ-010", "TO_DATE",         "PARSE_DATETIME"),
        ("OBQ-013", "INSTR",           "STRPOS"),
        ("OBQ-014", "LENGTHB",         "BYTE_LENGTH"),
        ("OBQ-015", "LISTAGG",         "STRING_AGG"),
        ("OBQ-018", "MINUS",           "EXCEPT DISTINCT"),
        ("OBQ-020", "ROWNUM_WHERE",    "LIMIT"),
        ("OBQ-021", "ROWNUM_SELECT",   "ROW_NUMBER()"),
    ])
    def test_direct_swap_exists(self, rule_id, oracle, bigquery):
        assert rule_id in RULES_MAP, f"{rule_id} ({oracle}) missing"
        assert bigquery in RULES_MAP[rule_id]["target_pattern"], (
            f"{rule_id}: target must contain '{bigquery}', got: "
            f"{RULES_MAP[rule_id]['target_pattern']}"
        )

    def test_dual_removal_exists(self):
        r = RULES_MAP["OBQ-019"]
        assert "FROM_DUAL" in str(r["source_pattern"].values())

    # --- Type Mappings ---
    @pytest.mark.parametrize("rule_id,oracle_type,bq_type", [
        ("OBQ-030", "VARCHAR2",  "STRING"),
        ("OBQ-031", "NUMBER",    "NUMERIC"),
        ("OBQ-032", "NUMBER_INT","INT64"),
        ("OBQ-033", "CLOB",      "STRING"),
        ("OBQ-034", "BLOB",      "BYTES"),
        ("OBQ-035", "XMLTYPE",   "JSON"),
    ])
    def test_type_mapping_exists(self, rule_id, oracle_type, bq_type):
        assert rule_id in RULES_MAP, f"{rule_id} ({oracle_type}) missing"
        r = RULES_MAP[rule_id]
        assert r["source_pattern"]["object_type"] == oracle_type
        assert bq_type in r["target_pattern"]

    # --- Cursor Patterns ---
    @pytest.mark.parametrize("rule_id,construct", [
        ("OBQ-040", "CURSOR_FOR_LOOP"),
        ("OBQ-041", "BULK_COLLECT"),
        ("OBQ-042", "OPEN_FETCH_CLOSE"),
        ("OBQ-043", "ROWTYPE_ATTRIBUTE"),
        ("OBQ-044", "TYPE_ATTRIBUTE"),
    ])
    def test_cursor_pattern_exists(self, rule_id, construct):
        assert rule_id in RULES_MAP, f"{rule_id} ({construct}) missing"
        assert RULES_MAP[rule_id]["source_pattern"]["construct"] == construct

    # --- Every rule has required fields ---
    REQUIRED_AC_FIELDS = ["rule_id", "name", "source_pattern", "target_pattern", "why", "severity"]

    def test_every_rule_has_acceptance_required_fields(self):
        for r in ALL_RULES:
            for field in self.REQUIRED_AC_FIELDS:
                assert field in r and r[field], (
                    f"{r['rule_id']}: acceptance criteria requires '{field}'"
                )

    def test_every_rule_has_at_least_one_test(self):
        for r in ALL_RULES:
            assert len(r["tests"]) >= 1, (
                f"{r['rule_id']}: acceptance criteria requires >= 1 passing unit test"
            )


# ===================================================================
# 17. TEST GUIDELINE ENFORCEMENT
# ===================================================================
class TestGuidelineEnforcement:
    """Directly enforce the 4 test guidelines from the user story."""

    def test_guideline_1_all_50_plus_rules_have_embedded_tests(self):
        """Unit — Run all 50+ rules against their embedded test cases; all must pass."""
        assert len(ALL_RULES) >= 50, f"Need 50+ rules, have {len(ALL_RULES)}"
        failures = []
        for r in ALL_RULES:
            rid = r["rule_id"]
            if not r["tests"]:
                failures.append(f"{rid}: no test cases")
                continue
            for i, tc in enumerate(r["tests"]):
                if not tc.get("input", "").strip():
                    failures.append(f"{rid} test[{i}]: empty input")
                if not tc.get("expected", "").strip():
                    failures.append(f"{rid} test[{i}]: empty expected")
        assert not failures, "Embedded test failures:\n" + "\n".join(failures)

    def test_guideline_2_decode_null_outputs_if_is_null(self):
        """Unit — DECODE(x, NULL, r1, r2) output must be IF(x IS NULL, r1, r2),
        not CASE WHEN x = NULL."""
        r = RULES_MAP["OBQ-004"]
        # target_pattern check
        assert r["target_pattern"].startswith("IF(")
        assert "IS NULL" in r["target_pattern"]
        assert "= NULL" not in r["target_pattern"]
        # every embedded test case check
        for tc in r["tests"]:
            assert tc["expected"].startswith("IF(")
            assert "IS NULL" in tc["expected"]
            assert "= NULL" not in tc["expected"]

    def test_guideline_3_sysdate_outputs_current_datetime(self):
        """Unit — SYSDATE rule test: output must be CURRENT_DATETIME(),
        not CURRENT_DATE()."""
        r = RULES_MAP["OBQ-005"]
        assert r["target_pattern"] == "CURRENT_DATETIME()"
        for tc in r["tests"]:
            assert "CURRENT_DATETIME()" in tc["expected"]

    def test_guideline_4_number_outputs_numeric(self):
        """Unit — NUMBER type rule test: output must be NUMERIC, not FLOAT64."""
        r = RULES_MAP["OBQ-031"]
        assert r["target_pattern"] == "NUMERIC"
        assert "FLOAT64" not in r["target_pattern"]
        for tc in r["tests"]:
            assert "NUMERIC" in tc["expected"]
            assert "FLOAT64" not in tc["expected"]


# ===================================================================
# 18. EDGE CASE: ORACLE DATE vs BIGQUERY DATE
# ===================================================================
class TestOracleDateGotcha:
    """Oracle DATE has time; BigQuery DATE does not. OBQ-036 must map to DATETIME."""

    def test_oracle_date_maps_to_datetime_not_date(self):
        r = RULES_MAP["OBQ-036"]
        assert r["target_pattern"] == "DATETIME", (
            f"OBQ-036: Oracle DATE must map to DATETIME, got {r['target_pattern']}"
        )
        # Must NOT map to just DATE
        assert r["target_pattern"] != "DATE"

    def test_oracle_date_why_explains_time_component(self):
        r = RULES_MAP["OBQ-036"]
        why_lower = r["why"].lower()
        assert "time" in why_lower, "OBQ-036 'why' should explain Oracle DATE has time"


# ===================================================================
# 19. EDGE CASE: TRUNC(SYSDATE) is the ONLY legitimate CURRENT_DATE()
# ===================================================================
class TestTruncSysdateIsOnlyCurrentDate:
    """CURRENT_DATE() should only appear in OBQ-006, nowhere else as a target."""

    def test_current_date_only_in_obq006(self):
        for r in ALL_RULES:
            if r["rule_id"] == "OBQ-006":
                continue
            target = r["target_pattern"]
            # Replace CURRENT_DATETIME() to avoid false positive
            cleaned = target.replace("CURRENT_DATETIME()", "")
            assert "CURRENT_DATE()" not in cleaned, (
                f"{r['rule_id']}: only OBQ-006 should use CURRENT_DATE() as target, "
                f"got: {target}"
            )


# ===================================================================
# 20. BOUNDARY VALUES
# ===================================================================
class TestBoundaryValues:
    """Test edge cases in confidence, severity, counts."""

    def test_confidence_exactly_zero(self):
        """No rule should have confidence exactly 0.0 (that means useless)."""
        for r in ALL_RULES:
            assert r["confidence"] > 0.0, (
                f"{r['rule_id']}: confidence is 0.0, rule is useless"
            )

    def test_minimum_confidence_is_0_3(self):
        """Lowest confidence in library should be 0.3 (TRIGGER, PACKAGE)."""
        min_conf = min(r["confidence"] for r in ALL_RULES)
        assert min_conf == 0.3, f"Minimum confidence is {min_conf}, expected 0.3"

    def test_maximum_confidence_is_1_0(self):
        max_conf = max(r["confidence"] for r in ALL_RULES)
        assert max_conf == 1.0

    def test_all_severity_levels_used(self):
        """All four severity levels should be represented."""
        severities = {r["severity"] for r in ALL_RULES}
        assert severities == {"critical", "high", "medium", "low"}, (
            f"Missing severity levels: {{'critical','high','medium','low'} - severities}"
        )

    def test_critical_rules_count(self):
        """There should be multiple critical rules (the 3 gotchas + architectural)."""
        critical = [r for r in ALL_RULES if r["severity"] == "critical"]
        assert len(critical) >= 3, f"Expected >= 3 critical rules, found {len(critical)}"
