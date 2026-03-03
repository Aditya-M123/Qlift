# tests/target/test_ta01a.py

import pytest
from qlift.target import ColumnProfile, TableProfile, TargetAdapter


# ─────────────────────────────────────────────
# Test 1 — TargetAdapter cannot be used directly
# ─────────────────────────────────────────────

def test_target_adapter_raises_type_error():
    """
    TargetAdapter is abstract.
    Trying to use it directly must raise TypeError.
    Only concrete adapters like BigQueryAdapter can be used.
    """
    with pytest.raises(TypeError):
        TargetAdapter()


# ─────────────────────────────────────────────
# Test 2 — TableProfile.columns returns List[ColumnProfile]
# ─────────────────────────────────────────────

def test_table_profile_columns_returns_list_of_column_profiles():
    """
    When TableProfile is created with 3 columns,
    .columns must return a list of ColumnProfile objects.
    """
    col1 = ColumnProfile(
        name="order_id",
        type="INT64",
        nullable=False,
        precision_warning=None
    )
    col2 = ColumnProfile(
        name="order_date",
        type="DATETIME",
        nullable=False,
        precision_warning=None
    )
    col3 = ColumnProfile(
        name="amount",
        type="NUMERIC",
        nullable=True,
        precision_warning="Verify decimal scale from source NUMBER(18,4)"
    )

    profile = TableProfile(
        sandbox_id="qlift_sandbox_test123",
        table_name="orders",
        row_count=500,
        columns=[col1, col2, col3]
    )

    # Must be a list
    assert isinstance(profile.columns, list)

    # Must have 3 items
    assert len(profile.columns) == 3

    # Every item must be a ColumnProfile
    for col in profile.columns:
        assert isinstance(col, ColumnProfile)


# ─────────────────────────────────────────────
# Test 3 — ColumnProfile stores values correctly
# ─────────────────────────────────────────────

def test_column_profile_stores_values_correctly():
    """
    ColumnProfile must store and return all field values correctly.
    """
    col = ColumnProfile(
        name="amount",
        type="NUMERIC",
        nullable=True,
        precision_warning="Check precision"
    )

    assert col.name              == "amount"
    assert col.type              == "NUMERIC"
    assert col.nullable          is True
    assert col.precision_warning == "Check precision"


# ─────────────────────────────────────────────
# Test 4 — precision_warning can be None
# ─────────────────────────────────────────────

def test_column_profile_precision_warning_can_be_none():
    """
    Not every column has a precision warning.
    precision_warning must accept None.
    """
    col = ColumnProfile(
        name="order_id",
        type="INT64",
        nullable=False,
        precision_warning=None
    )

    assert col.precision_warning is None


# ─────────────────────────────────────────────
# Test 5 — No BigQuery SDK imports in contract files
# ─────────────────────────────────────────────

def test_no_bigquery_imports_in_contract_files():
    """
    adapter.py and schemas.py must have zero BigQuery SDK imports.
    Only checks actual import lines — not comments or docstrings.
    The contract must stay clean and database-agnostic.
    """
    import qlift.target.ta01a.adapter as adapter_module
    import qlift.target.ta01a.schemas as schemas_module

    for module in [adapter_module, schemas_module]:
        source = open(module.__file__).read()
        lines = source.splitlines()

        for line in lines:
            stripped = line.strip()
            # Only check actual import statements
            if stripped.startswith("import") or stripped.startswith("from"):
                assert "google.cloud" not in stripped, (
                    f"Found google.cloud import in {module.__file__}:\n{line}"
                )
                assert "google.cloud.bigquery" not in stripped, (
                    f"Found bigquery SDK import in {module.__file__}:\n{line}"
                )


# ─────────────────────────────────────────────
# Test 6 — TableProfile stores row_count correctly
# ─────────────────────────────────────────────

def test_table_profile_stores_row_count():
    """
    TableProfile must store and return all field values correctly.
    """
    profile = TableProfile(
        sandbox_id="sandbox_001",
        table_name="orders",
        row_count=9999,
        columns=[]
    )

    assert profile.row_count  == 9999
    assert profile.table_name == "orders"
    assert profile.sandbox_id == "sandbox_001"