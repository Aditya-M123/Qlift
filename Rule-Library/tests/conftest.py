"""Shared fixtures for the Oracle-to-BigQuery rule test suite."""

import pathlib
from typing import Any

import pytest
import yaml

RULES_DIR = pathlib.Path(__file__).resolve().parent.parent / "rules"


def _load_yaml_files(directory: pathlib.Path) -> list[dict[str, Any]]:
    """Recursively load all YAML rule files under *directory*."""
    rules: list[dict[str, Any]] = []
    for yaml_file in sorted(directory.rglob("*.yaml")):
        # Skip the template file
        if yaml_file.name == "RULE_TEMPLATE.yaml":
            continue
        with open(yaml_file, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, list):
            rules.extend(data)
    return rules


@pytest.fixture(scope="session")
def all_rules() -> list[dict[str, Any]]:
    """Return every rule loaded from rules/."""
    return _load_yaml_files(RULES_DIR)


@pytest.fixture(scope="session")
def oracle_rules() -> list[dict[str, Any]]:
    """Return only Oracle-to-BigQuery rules (OBQ-*)."""
    return _load_yaml_files(RULES_DIR / "oracle-to-bigquery")


@pytest.fixture(scope="session")
def shared_rules() -> list[dict[str, Any]]:
    """Return only shared BigQuery rules (SBQ-*)."""
    return _load_yaml_files(RULES_DIR / "shared")


@pytest.fixture(scope="session")
def rules_by_id(all_rules) -> dict[str, dict[str, Any]]:
    """Return a dict mapping rule_id → rule for fast lookup."""
    return {r["rule_id"]: r for r in all_rules}


def _load_rules_from_file(relative_path: str) -> list[dict[str, Any]]:
    """Load rules from a specific file relative to rules/."""
    yaml_file = RULES_DIR / relative_path
    with open(yaml_file, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, list) else []


@pytest.fixture(scope="session")
def null_handling_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/direct_swaps/null_handling.yaml")


@pytest.fixture(scope="session")
def datetime_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/direct_swaps/datetime_functions.yaml")


@pytest.fixture(scope="session")
def string_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/direct_swaps/string_functions.yaml")


@pytest.fixture(scope="session")
def set_and_misc_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/direct_swaps/set_and_misc.yaml")


@pytest.fixture(scope="session")
def type_mapping_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/type_mapping/type_mapping.yaml")


@pytest.fixture(scope="session")
def cursor_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/architectural/cursor_patterns.yaml")


@pytest.fixture(scope="session")
def ddl_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/architectural/ddl_objects.yaml")


@pytest.fixture(scope="session")
def structural_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("oracle-to-bigquery/structural/structural_patterns.yaml")


@pytest.fixture(scope="session")
def bigquery_rules() -> list[dict[str, Any]]:
    return _load_rules_from_file("shared/bigquery/bigquery_patterns.yaml")
