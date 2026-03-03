from typing import Dict


# ─────────────────────────────────────────────
# Oracle → BigQuery Type Mapping Table
# ─────────────────────────────────────────────
#
# Two critical rules:
#
# 1. Oracle DATE   → BigQuery DATETIME  (NOT DATE)
#    Oracle DATE stores date AND time e.g. 2024-01-15 14:32:00
#    BigQuery DATE stores only date   e.g. 2024-01-15
#    If we map DATE → DATE we silently lose the time component
#
# 2. Oracle NUMBER → BigQuery NUMERIC   (NOT FLOAT64)
#    Oracle NUMBER has exact precision
#    BigQuery FLOAT64 loses decimal precision
#    Bad for financial data e.g. 99.99 becomes 99.98999999
#
# ─────────────────────────────────────────────

ORACLE_TO_BIGQUERY: Dict[str, str] = {

    # ── String Types ─────────────────────────
    "VARCHAR2":      "STRING",
    "NVARCHAR2":     "STRING",
    "CHAR":          "STRING",
    "NCHAR":         "STRING",
    "CLOB":          "STRING",
    "NCLOB":         "STRING",
    "LONG":          "STRING",

    # ── Numeric Types ────────────────────────
    "NUMBER":        "NUMERIC",       # NOT FLOAT64 — preserves precision
    "NUMBER(p,0)":   "INT64",         # whole numbers only
    "NUMBER(p,s)":   "NUMERIC",       # exact decimal precision kept
    "INTEGER":       "INT64",
    "INT":           "INT64",
    "SMALLINT":      "INT64",
    "FLOAT":         "FLOAT64",
    "BINARY_FLOAT":  "FLOAT64",
    "BINARY_DOUBLE": "FLOAT64",

    # ── Date and Time Types ──────────────────
    "DATE":          "DATETIME",      # NOT DATE — Oracle DATE has time component
    "TIMESTAMP":     "TIMESTAMP",

    # ── Binary Types ─────────────────────────
    "BLOB":          "BYTES",
    "RAW":           "BYTES",
    "LONG RAW":      "BYTES",

    # ── Special Types ────────────────────────
    "XMLTYPE":       "JSON",          # lossy — XML to JSON loses some features
    "ROWID":         "STRING",
    "UROWID":        "STRING",
}


# Types that may lose data during conversion
# These will trigger a precision_warning in ColumnProfile
LOSSY_MAPPINGS = {
    "XMLTYPE",       # XML structure may not fully convert to JSON
    "FLOAT",         # precision may differ
    "BINARY_FLOAT",  # precision may differ
    "BINARY_DOUBLE", # precision may differ
}


def get_type_mapping(source_dialect: str) -> Dict[str, str]:
    """
    Return the type conversion table for the given source dialect.

    Args:
        source_dialect: name of source database e.g. "oracle"

    Returns:
        Dict mapping source types to BigQuery types

    Raises:
        ValueError: if source dialect is not supported
    """
    if source_dialect.lower() == "oracle":
        return ORACLE_TO_BIGQUERY

    raise ValueError(
        f"Unsupported source dialect: '{source_dialect}'. "
        f"Currently supported: ['oracle']"
    )


def get_bigquery_type(source_type: str, source_dialect: str = "oracle") -> str:
    """
    Return the BigQuery type for a given source type.
    Falls back to STRING if type is not found in mapping.

    Args:
        source_type: Oracle type name e.g. "VARCHAR2", "DATE"
        source_dialect: source database name e.g. "oracle"

    Returns:
        BigQuery type string e.g. "STRING", "DATETIME"
    """
    mapping = get_type_mapping(source_dialect)
    return mapping.get(source_type.upper(), "STRING")


def is_lossy(source_type: str) -> bool:
    """
    Check if converting this source type may lose data.

    Args:
        source_type: Oracle type name e.g. "XMLTYPE"

    Returns:
        True if conversion may be lossy, False otherwise
    """
    return source_type.upper() in LOSSY_MAPPINGS