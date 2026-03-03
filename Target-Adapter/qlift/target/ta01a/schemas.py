# qlift/target/ta01a/schemas.py

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ColumnProfile:
    """
    Holds information about a single column
    inside a sandbox table after profiling.

    Example:
        ColumnProfile(
            name="order_date",
            type="DATETIME",
            nullable=False,
            precision_warning=None
        )
    """
    name: str
    # column name e.g. "order_date"

    type: str
    # target database type e.g. "DATETIME", "INT64", "NUMERIC"

    nullable: bool
    # True if column allows NULL values, False if NOT NULL

    precision_warning: Optional[str]
    # Warning message if data loss is possible
    # e.g. "NUMBER→FLOAT64 may lose decimal precision"
    # None if no warning needed


@dataclass
class TableProfile:
    """
    Holds statistics and metadata about an entire
    sandbox table after profiling.

    Example:
        TableProfile(
            sandbox_id="qlift_sandbox_abc123",
            table_name="orders",
            row_count=5000,
            columns=[col1, col2, col3]
        )
    """
    sandbox_id: str
    # which sandbox this profile came from
    # e.g. "qlift_sandbox_abc123"

    table_name: str
    # name of the table that was profiled
    # e.g. "orders"

    row_count: int
    # total number of rows in the table
    # e.g. 5000

    columns: List[ColumnProfile]
    # one ColumnProfile per column in the table
