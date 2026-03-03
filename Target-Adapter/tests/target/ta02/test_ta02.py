# tests/target/test_ta02.py

import os
import pytest
from qlift.target.ta02.bigquery.adapter import BigQueryAdapter
from qlift.target.ta02.bigquery.type_mapping import get_type_mapping, is_lossy
from qlift.target.ta02.bigquery.ddl_generator import generate_ddl


# ─────────────────────────────────────────────
# Type Mapping Tests — no GCP needed
# ─────────────────────────────────────────────

def test_oracle_date_maps_to_datetime():
    """
    Oracle DATE must map to DATETIME not DATE.
    Oracle DATE stores time component — BigQuery DATE does not.
    Silent data loss if mapped incorrectly.
    """
    mapping = get_type_mapping("oracle")
    assert mapping["DATE"] == "DATETIME"
    assert mapping["DATE"] != "DATE"


def test_oracle_number_maps_to_numeric():
    """
    Oracle NUMBER must map to NUMERIC not FLOAT64.
    FLOAT64 loses decimal precision — bad for financial data.
    """
    mapping = get_type_mapping("oracle")
    assert mapping["NUMBER"] == "NUMERIC"
    assert mapping["NUMBER"] != "FLOAT64"


def test_oracle_varchar2_maps_to_string():
    mapping = get_type_mapping("oracle")
    assert mapping["VARCHAR2"] == "STRING"


def test_oracle_clob_maps_to_string():
    mapping = get_type_mapping("oracle")
    assert mapping["CLOB"] == "STRING"


def test_oracle_blob_maps_to_bytes():
    mapping = get_type_mapping("oracle")
    assert mapping["BLOB"] == "BYTES"


def test_oracle_timestamp_maps_to_timestamp():
    mapping = get_type_mapping("oracle")
    assert mapping["TIMESTAMP"] == "TIMESTAMP"


def test_oracle_integer_maps_to_int64():
    mapping = get_type_mapping("oracle")
    assert mapping["INTEGER"] == "INT64"


def test_xmltype_is_lossy():
    """XMLTYPE conversion to JSON may lose data."""
    assert is_lossy("XMLTYPE") is True


def test_varchar2_is_not_lossy():
    """VARCHAR2 conversion to STRING is safe."""
    assert is_lossy("VARCHAR2") is False


def test_unsupported_dialect_raises_value_error():
    """Unsupported source dialect must raise ValueError."""
    with pytest.raises(ValueError):
        get_type_mapping("unsupported_db")


# ─────────────────────────────────────────────
# DDL Generation Tests — no GCP needed
# ─────────────────────────────────────────────

def test_generate_ddl_contains_partition_by():
    """
    When partition_column is in recommendations,
    DDL must contain PARTITION BY clause.
    """
    schema_def = {
        "project":    "my-project",
        "dataset":    "sales",
        "table_name": "orders",
        "columns": [
            {"name": "order_id",   "source_type": "NUMBER",   "nullable": False},
            {"name": "order_date", "source_type": "DATE",     "nullable": False},
            {"name": "amount",     "source_type": "NUMBER",   "nullable": True},
        ]
    }
    recommendations = {
        "partition_column": "order_date",
        "cluster_columns":  []
    }

    ddl = generate_ddl(schema_def, recommendations)

    assert "PARTITION BY" in ddl
    assert "order_date"   in ddl


def test_generate_ddl_contains_cluster_by():
    """
    When cluster_columns is in recommendations,
    DDL must contain CLUSTER BY clause.
    """
    schema_def = {
        "project":    "my-project",
        "dataset":    "sales",
        "table_name": "orders",
        "columns": [
            {"name": "order_id",    "source_type": "NUMBER",   "nullable": False},
            {"name": "customer_id", "source_type": "NUMBER",   "nullable": False},
        ]
    }
    recommendations = {
        "partition_column": "",
        "cluster_columns":  ["customer_id"]
    }

    ddl = generate_ddl(schema_def, recommendations)

    assert "CLUSTER BY"   in ddl
    assert "customer_id"  in ddl


def test_generate_ddl_contains_correct_types():
    """
    Generated DDL must use BigQuery types not Oracle types.
    DATE column must become DATETIME in the DDL.
    NUMBER column must become NUMERIC in the DDL.
    """
    schema_def = {
        "project":    "my-project",
        "dataset":    "sales",
        "table_name": "orders",
        "columns": [
            {"name": "order_date", "source_type": "DATE",   "nullable": True},
            {"name": "amount",     "source_type": "NUMBER", "nullable": True},
        ]
    }
    recommendations = {}

    ddl = generate_ddl(schema_def, recommendations)

    assert "DATETIME" in ddl   # DATE → DATETIME
    assert "NUMERIC"  in ddl   # NUMBER → NUMERIC
    assert "DATE"     not in ddl.replace("DATETIME", "").replace("PARTITION", "")


def test_generate_ddl_contains_not_null():
    """
    Non-nullable columns must have NOT NULL in DDL.
    """
    schema_def = {
        "project":    "my-project",
        "dataset":    "sales",
        "table_name": "orders",
        "columns": [
            {"name": "order_id", "source_type": "NUMBER", "nullable": False},
        ]
    }
    recommendations = {}

    ddl = generate_ddl(schema_def, recommendations)

    assert "NOT NULL" in ddl


def test_generate_ddl_table_reference_format():
    """
    Table reference must be in correct BigQuery format.
    e.g. `project.dataset.table`
    """
    schema_def = {
        "project":    "my-project",
        "dataset":    "sales",
        "table_name": "orders",
        "columns":    []
    }
    recommendations = {}

    ddl = generate_ddl(schema_def, recommendations)

    assert "my-project.sales.orders" in ddl


# ─────────────────────────────────────────────
# BigQueryAdapter Unit Tests — no GCP needed
# ─────────────────────────────────────────────

def test_adapter_get_dialect_name():
    adapter = BigQueryAdapter()
    assert adapter.get_dialect_name() == "bigquery"


def test_adapter_not_connected_raises_error():
    """
    Calling any method before connect() must raise RuntimeError.
    """
    adapter = BigQueryAdapter()
    with pytest.raises(RuntimeError, match="not connected"):
        adapter.create_sandbox("test")


def test_adapter_connect_requires_project_id():
    """
    connect() must raise ValueError if project_id is missing.
    """
    adapter = BigQueryAdapter()
    with pytest.raises(ValueError, match="project_id"):
        adapter.connect({})


def test_adapter_get_type_mapping_returns_dict():
    adapter = BigQueryAdapter()
    mapping = adapter.get_type_mapping("oracle")
    assert isinstance(mapping, dict)
    assert len(mapping) > 0


def test_adapter_generate_ddl_returns_string():
    adapter    = BigQueryAdapter()
    schema_def = {
        "project":    "my-project",
        "dataset":    "sales",
        "table_name": "orders",
        "columns": [
            {"name": "id", "source_type": "NUMBER", "nullable": False}
        ]
    }
    ddl = adapter.generate_ddl(schema_def, {})
    assert isinstance(ddl, str)
    assert "CREATE TABLE" in ddl


# ─────────────────────────────────────────────
# Integration Test — requires live GCP project
# ─────────────────────────────────────────────

@pytest.mark.integration
def test_adapter_connect_via_workload_identity():
    """
    Integration — Given a real GCP project,
    When connect() is called,
    Then BigQuery client is successfully initialised via Workload Identity.

    Requires:
        - GCP_PROJECT_ID env var set
        - gcloud auth application-default login (local dev)
          OR Workload Identity (GKE)
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "q-mercato-dev")

    adapter = BigQueryAdapter()
    adapter.connect({"project_id": project_id})

    # Client must be initialised
    assert adapter.client is not None

    # Project ID must be stored
    assert adapter.project_id == project_id

    # Dialect must be bigquery
    assert adapter.get_dialect_name() == "bigquery"