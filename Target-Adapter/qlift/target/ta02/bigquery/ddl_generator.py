# qlift/target/ta02/bigquery/ddl_generator.py

from typing import Dict, List
from qlift.target.ta02.bigquery.type_mapping import get_bigquery_type, is_lossy


def generate_ddl(schema_def: dict, recommendations: dict) -> str:
    """
    Generate a BigQuery CREATE TABLE statement.
    Includes PARTITION BY and CLUSTER BY from recommendations.

    Args:
        schema_def: table definition as dict
            e.g. {
                "project":    "my-gcp-project",
                "dataset":    "sales",
                "table_name": "orders",
                "columns": [
                    {
                        "name":        "order_id",
                        "source_type": "NUMBER(10,0)",
                        "nullable":    False
                    },
                    ...
                ]
            }

        recommendations: partition and cluster suggestions
            e.g. {
                "partition_column":  "order_date",
                "cluster_columns":   ["customer_id", "status"]
            }

    Returns:
        str: complete CREATE TABLE SQL string ready to execute

    Example output:
        CREATE TABLE `my-gcp-project.sales.orders`
        (
          order_id    INT64     NOT NULL,
          order_date  DATETIME  NOT NULL,
          amount      NUMERIC
        )
        PARTITION BY DATE(order_date)
        CLUSTER BY customer_id, status;
    """

    project    = schema_def.get("project", "")
    dataset    = schema_def.get("dataset", "")
    table_name = schema_def.get("table_name", "")
    columns    = schema_def.get("columns", [])

    # ── Build table reference ────────────────
    if project and dataset:
        table_ref = f"`{project}.{dataset}.{table_name}`"
    elif dataset:
        table_ref = f"`{dataset}.{table_name}`"
    else:
        table_ref = f"`{table_name}`"

    # ── Build column definitions ─────────────
    col_lines = _build_column_lines(columns)
    cols_sql  = ",\n".join(col_lines)

    # ── Build PARTITION BY clause ────────────
    partition_clause = _build_partition_clause(recommendations)

    # ── Build CLUSTER BY clause ──────────────
    cluster_clause = _build_cluster_clause(recommendations)

    # ── Assemble final DDL ───────────────────
    ddl = (
        f"CREATE TABLE {table_ref}\n"
        f"(\n"
        f"{cols_sql}\n"
        f")"
        f"{partition_clause}"
        f"{cluster_clause};"
    )

    return ddl


def _build_column_lines(columns: List[dict]) -> List[str]:
    """
    Build column definition lines for the CREATE TABLE statement.

    Args:
        columns: list of column dicts with name, source_type, nullable

    Returns:
        List of formatted column definition strings
    """
    lines = []

    for col in columns:
        name        = col.get("name", "unknown")
        source_type = col.get("source_type", "VARCHAR2")
        nullable    = col.get("nullable", True)

        # Convert Oracle type to BigQuery type
        bq_type = get_bigquery_type(source_type)

        # Add NOT NULL if column is not nullable
        null_clause = "" if nullable else "  NOT NULL"

        # Add lossy warning as SQL comment
        lossy_comment = ""
        if is_lossy(source_type):
            lossy_comment = f"  -- WARNING: lossy conversion from {source_type}"

        lines.append(
            f"  {name:<30} {bq_type}{null_clause}{lossy_comment}"
        )

    return lines


def _build_partition_clause(recommendations: dict) -> str:
    """
    Build the PARTITION BY clause from recommendations.

    BigQuery supports partitioning by:
    - DATE column      → PARTITION BY DATE(column_name)
    - DATETIME column  → PARTITION BY DATE(column_name)
    - TIMESTAMP column → PARTITION BY DATE(column_name)
    - INT64 column     → PARTITION BY RANGE_BUCKET(...)

    Args:
        recommendations: dict with partition_column key

    Returns:
        PARTITION BY clause string or empty string
    """
    partition_col = recommendations.get("partition_column", "")

    if not partition_col:
        return ""

    return f"\nPARTITION BY DATE({partition_col})"


def _build_cluster_clause(recommendations: dict) -> str:
    """
    Build the CLUSTER BY clause from recommendations.
    BigQuery supports up to 4 cluster columns.

    Args:
        recommendations: dict with cluster_columns key

    Returns:
        CLUSTER BY clause string or empty string
    """
    cluster_cols = recommendations.get("cluster_columns", [])

    if not cluster_cols:
        return ""

    # BigQuery max 4 cluster columns
    cluster_cols = cluster_cols[:4]
    cols_str     = ", ".join(cluster_cols)

    return f"\nCLUSTER BY {cols_str}"
