"""Ensure all 54 expected rule IDs are present in the library."""

import pytest

# fmt: off
EXPECTED_OBQ_IDS = [
    # Direct swaps — null handling
    "OBQ-001", "OBQ-002", "OBQ-003", "OBQ-004",
    # Direct swaps — datetime
    "OBQ-005", "OBQ-006", "OBQ-007", "OBQ-008",
    "OBQ-009", "OBQ-010", "OBQ-011", "OBQ-012",
    # Direct swaps — string
    "OBQ-013", "OBQ-014", "OBQ-015", "OBQ-016", "OBQ-017",
    # Direct swaps — set & misc
    "OBQ-018", "OBQ-019", "OBQ-020", "OBQ-021", "OBQ-022",
    # Type mapping
    "OBQ-030", "OBQ-031", "OBQ-032", "OBQ-033", "OBQ-034",
    "OBQ-035", "OBQ-036", "OBQ-037", "OBQ-038", "OBQ-039",
    # Architectural — cursors
    "OBQ-040", "OBQ-041", "OBQ-042", "OBQ-043", "OBQ-044",
    # Architectural — DDL
    "OBQ-045", "OBQ-046", "OBQ-047", "OBQ-048", "OBQ-049", "OBQ-050",
    # Structural
    "OBQ-051", "OBQ-052", "OBQ-053", "OBQ-054", "OBQ-055", "OBQ-056",
]

EXPECTED_SBQ_IDS = [
    "SBQ-001", "SBQ-002", "SBQ-003", "SBQ-004", "SBQ-005",
]
# fmt: on

ALL_EXPECTED_IDS = EXPECTED_OBQ_IDS + EXPECTED_SBQ_IDS


class TestRuleCoverage:
    """Verify every expected rule ID is present exactly once."""

    def test_total_rule_count(self, all_rules):
        assert len(all_rules) == 54, (
            f"Expected 54 rules, found {len(all_rules)}"
        )

    def test_all_obq_ids_present(self, rules_by_id):
        missing = [rid for rid in EXPECTED_OBQ_IDS if rid not in rules_by_id]
        assert not missing, f"Missing OBQ rule IDs: {missing}"

    def test_all_sbq_ids_present(self, rules_by_id):
        missing = [rid for rid in EXPECTED_SBQ_IDS if rid not in rules_by_id]
        assert not missing, f"Missing SBQ rule IDs: {missing}"

    def test_no_unexpected_ids(self, rules_by_id):
        expected_set = set(ALL_EXPECTED_IDS)
        unexpected = [rid for rid in rules_by_id if rid not in expected_set]
        assert not unexpected, f"Unexpected rule IDs: {unexpected}"

    @pytest.mark.parametrize("rule_id", ALL_EXPECTED_IDS)
    def test_individual_rule_exists(self, rules_by_id, rule_id):
        assert rule_id in rules_by_id, f"Rule {rule_id} not found"
