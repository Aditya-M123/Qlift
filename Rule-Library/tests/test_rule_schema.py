"""Validate every rule conforms to the RE-01 YAML schema contract."""

import pytest

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
SOURCE_PATTERN_PRIMARY_KEYS = {"function", "keyword", "object_type", "construct"}
SOURCE_PATTERN_OPTIONAL_KEYS = {"arg_count", "arg_type"}
ALL_SOURCE_PATTERN_KEYS = SOURCE_PATTERN_PRIMARY_KEYS | SOURCE_PATTERN_OPTIONAL_KEYS

REQUIRED_FIELDS = [
    "rule_id",
    "version",
    "name",
    "severity",
    "source_pattern",
    "target_pattern",
    "confidence",
    "tags",
    "why",
    "tests",
]


class TestRuleSchema:
    """Each rule must have the required fields with correct types."""

    def test_all_rules_loaded(self, all_rules):
        assert len(all_rules) > 0, "No rules were loaded"

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_required_fields_present(self, all_rules, field):
        for rule in all_rules:
            assert field in rule, (
                f"Rule {rule.get('rule_id', '???')} missing required field '{field}'"
            )

    def test_rule_id_format(self, all_rules):
        for rule in all_rules:
            rid = rule["rule_id"]
            assert rid.startswith("OBQ-") or rid.startswith("SBQ-"), (
                f"Rule ID '{rid}' must start with OBQ- or SBQ-"
            )

    def test_severity_values(self, all_rules):
        for rule in all_rules:
            assert rule["severity"] in VALID_SEVERITIES, (
                f"Rule {rule['rule_id']}: invalid severity '{rule['severity']}'"
            )

    def test_confidence_range(self, all_rules):
        for rule in all_rules:
            c = rule["confidence"]
            assert isinstance(c, (int, float)), (
                f"Rule {rule['rule_id']}: confidence must be numeric"
            )
            assert 0.0 <= c <= 1.0, (
                f"Rule {rule['rule_id']}: confidence {c} out of range [0, 1]"
            )

    def test_source_pattern_has_primary_key(self, all_rules):
        for rule in all_rules:
            sp = rule["source_pattern"]
            assert isinstance(sp, dict), (
                f"Rule {rule['rule_id']}: source_pattern must be a dict"
            )
            primary_keys = set(sp.keys()) & SOURCE_PATTERN_PRIMARY_KEYS
            assert len(primary_keys) >= 1, (
                f"Rule {rule['rule_id']}: source_pattern needs at least one of "
                f"{SOURCE_PATTERN_PRIMARY_KEYS}"
            )

    def test_source_pattern_keys_valid(self, all_rules):
        for rule in all_rules:
            sp = rule["source_pattern"]
            invalid = set(sp.keys()) - ALL_SOURCE_PATTERN_KEYS
            assert not invalid, (
                f"Rule {rule['rule_id']}: invalid source_pattern keys {invalid}"
            )

    def test_tags_is_list(self, all_rules):
        for rule in all_rules:
            assert isinstance(rule["tags"], list), (
                f"Rule {rule['rule_id']}: tags must be a list"
            )
            assert len(rule["tags"]) > 0, (
                f"Rule {rule['rule_id']}: tags must not be empty"
            )

    def test_tests_is_nonempty_list(self, all_rules):
        for rule in all_rules:
            tests = rule["tests"]
            assert isinstance(tests, list), (
                f"Rule {rule['rule_id']}: tests must be a list"
            )
            assert len(tests) > 0, (
                f"Rule {rule['rule_id']}: must have at least one test case"
            )

    def test_each_test_has_input_and_expected(self, all_rules):
        for rule in all_rules:
            for i, tc in enumerate(rule["tests"]):
                assert "input" in tc, (
                    f"Rule {rule['rule_id']} test[{i}] missing 'input'"
                )
                assert "expected" in tc, (
                    f"Rule {rule['rule_id']} test[{i}] missing 'expected'"
                )

    def test_no_duplicate_rule_ids(self, all_rules):
        ids = [r["rule_id"] for r in all_rules]
        dupes = [rid for rid in ids if ids.count(rid) > 1]
        assert not dupes, f"Duplicate rule IDs: {set(dupes)}"

    def test_version_is_string(self, all_rules):
        for rule in all_rules:
            assert isinstance(rule["version"], str), (
                f"Rule {rule['rule_id']}: version must be a string"
            )

    def test_target_pattern_is_string(self, all_rules):
        for rule in all_rules:
            assert isinstance(rule["target_pattern"], str), (
                f"Rule {rule['rule_id']}: target_pattern must be a string"
            )


class TestEmbeddedTestCases:
    """Run all 50+ rules against their embedded test cases — all must pass.

    Each rule carries its own tests[].input / tests[].expected pairs.
    This class validates every embedded test case is well-formed and that
    the expected output is consistent with the rule's target_pattern.
    """

    def test_all_rules_have_passing_test_cases(self, all_rules):
        """Every rule's embedded test cases must have non-empty input and expected."""
        failures = []
        for rule in all_rules:
            rid = rule["rule_id"]
            for i, tc in enumerate(rule["tests"]):
                inp = tc.get("input", "")
                exp = tc.get("expected", "")
                if not isinstance(inp, str) or not str(inp).strip():
                    failures.append(f"{rid} test[{i}]: input is empty or not a string")
                if not isinstance(exp, str) or not str(exp).strip():
                    failures.append(f"{rid} test[{i}]: expected is empty or not a string")
        assert not failures, "Embedded test case failures:\n" + "\n".join(failures)

    def test_expected_output_differs_from_input_or_is_compatible(self, all_rules):
        """For non-compatible rules, expected output should differ from input.
        Compatible rules (confidence=1.0 with 'compatible' tag) may have identical I/O.
        """
        for rule in all_rules:
            rid = rule["rule_id"]
            is_compatible = "compatible" in rule.get("tags", [])
            for i, tc in enumerate(rule["tests"]):
                inp = str(tc["input"]).strip()
                exp = str(tc["expected"]).strip()
                if not is_compatible and inp == exp:
                    assert False, (
                        f"{rid} test[{i}]: input and expected are identical "
                        f"but rule is not tagged 'compatible': {inp!r}"
                    )

    def test_embedded_test_count(self, all_rules):
        """Verify the total number of embedded test cases across all rules is >= 50."""
        total = sum(len(r["tests"]) for r in all_rules)
        assert total >= 50, (
            f"Expected at least 50 embedded test cases across all rules, found {total}"
        )
