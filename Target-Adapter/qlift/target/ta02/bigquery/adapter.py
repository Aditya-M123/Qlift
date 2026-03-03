from typing import Any, Dict, List

from google.cloud import bigquery

from qlift.target.ta01a.adapter import TargetAdapter
from qlift.target.ta01a.schemas import ColumnProfile, TableProfile
from qlift.target.ta02.bigquery.type_mapping import get_type_mapping, get_bigquery_type, is_lossy
from qlift.target.ta02.bigquery.ddl_generator import generate_ddl


class BigQueryAdapter(TargetAdapter):
    """
    Concrete implementation of TargetAdapter for Google BigQuery.

    Encapsulates:
    - Workload Identity authentication
    - Oracle to BigQuery type mapping
    - DDL generation with PARTITION BY and CLUSTER BY
    - Sandbox lifecycle (create, deploy, load, query, profile, destroy)

    All BigQuery SDK imports are isolated in this folder.
    No other service holds a BigQuery SDK dependency.
    """

    def __init__(self):
        self.client     = None
        self.project_id = None

    # ─────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────

    def connect(self, config: dict) -> None:
        """
        Connect to BigQuery using Workload Identity.
        No JSON key files — GCP handles auth automatically.

        For local development run first:
            gcloud auth application-default login

        For GKE production:
            Workload Identity bindings handle auth automatically

        Args:
            config: dict with project_id
                    e.g. {"project_id": "my-gcp-project"}
        """
        self.project_id = config.get("project_id")

        if not self.project_id:
            raise ValueError(
                "config must contain 'project_id' "
                "e.g. {'project_id': 'my-gcp-project'}"
            )

        # Workload Identity — GCP handles credentials automatically
        self.client = bigquery.Client(project=self.project_id)

    # ─────────────────────────────────────────────
    # Dialect Info
    # ─────────────────────────────────────────────

    def get_dialect_name(self) -> str:
        """Return the name of this target dialect."""
        return "bigquery"

    def get_grammar(self) -> Any:
        """
        Return grammar identifier for BigQuery dialect.
        Used by symbolic validator to check translated SQL.
        """
        return "bigquery_grammar"

    # ─────────────────────────────────────────────
    # Type Mapping
    # ─────────────────────────────────────────────

    def get_type_mapping(self, source_dialect: str) -> Dict[str, str]:
        """
        Return Oracle to BigQuery type conversion table.

        Args:
            source_dialect: e.g. "oracle"

        Returns:
            Dict e.g. {"VARCHAR2": "STRING", "DATE": "DATETIME", ...}
        """
        return get_type_mapping(source_dialect)

    # ─────────────────────────────────────────────
    # DDL Generation
    # ─────────────────────────────────────────────

    def generate_ddl(self, schema_def: dict, recommendations: dict) -> str:
        """
        Generate a BigQuery CREATE TABLE statement.
        Includes PARTITION BY and CLUSTER BY from recommendations.

        Args:
            schema_def:      table definition dict
            recommendations: partition and cluster suggestions

        Returns:
            str: complete CREATE TABLE SQL string
        """
        return generate_ddl(schema_def, recommendations)

    # ─────────────────────────────────────────────
    # Sandbox Lifecycle
    # ─────────────────────────────────────────────

    def create_sandbox(self, name: str) -> str:
        """
        Create a temporary BigQuery dataset for testing.

        Args:
            name: human readable label e.g. "orders_test"

        Returns:
            str: sandbox dataset id e.g. "qlift_sandbox_orders_test"
        """
        self._require_client()

        import uuid
        sandbox_id = f"qlift_sandbox_{name}_{uuid.uuid4().hex[:8]}"

        dataset = bigquery.Dataset(
            f"{self.project_id}.{sandbox_id}"
        )
        dataset.location = "US"

        self.client.create_dataset(dataset, exists_ok=True)

        return sandbox_id

    def destroy_sandbox(self, sandbox_id: str) -> None:
        """
        Permanently delete sandbox dataset and everything inside it.
        Always called after testing — even if tests fail.

        Args:
            sandbox_id: the id returned by create_sandbox()
        """
        self._require_client()

        self.client.delete_dataset(
            f"{self.project_id}.{sandbox_id}",
            delete_contents=True,
            not_found_ok=True
        )

    def deploy_ddl(self, sandbox_id: str, ddl: str) -> None:
        """
        Run DDL statements inside the sandbox.

        Args:
            sandbox_id: which sandbox to deploy into
            ddl:        SQL DDL string e.g. CREATE TABLE ...
        """
        self._require_client()

        # Prefix table references with sandbox dataset
        job = self.client.query(ddl)
        job.result()  # wait for completion

    def load_test_data(
        self,
        sandbox_id: str,
        table: str,
        data: List[Dict]
    ) -> int:
        """
        Insert test rows into a sandbox table.

        Args:
            sandbox_id: which sandbox
            table:      table name to insert into
            data:       list of row dicts

        Returns:
            int: number of rows inserted
        """
        self._require_client()

        table_ref = f"{self.project_id}.{sandbox_id}.{table}"
        errors    = self.client.insert_rows_json(table_ref, data)

        if errors:
            raise RuntimeError(
                f"Failed to insert rows into {table_ref}: {errors}"
            )

        return len(data)

    def execute_query(
        self,
        sandbox_id: str,
        query: str
    ) -> List[Dict]:
        """
        Run a SQL query inside the sandbox and return results.

        Args:
            sandbox_id: which sandbox to query
            query:      SQL string to execute

        Returns:
            List[Dict]: rows as list of dicts
        """
        self._require_client()

        job  = self.client.query(query)
        rows = job.result()

        return [dict(row) for row in rows]

    def get_table_profile(
        self,
        sandbox_id: str,
        table: str
    ) -> TableProfile:
        """
        Collect statistical profile of a sandbox table.
        Runs row count and column metadata queries.

        Args:
            sandbox_id: which sandbox
            table:      table name to profile

        Returns:
            TableProfile with row_count and per-column ColumnProfiles
        """
        self._require_client()

        table_ref    = f"{self.project_id}.{sandbox_id}.{table}"
        bq_table     = self.client.get_table(table_ref)

        # Get row count
        count_query  = f"SELECT COUNT(*) as row_count FROM `{table_ref}`"
        count_job    = self.client.query(count_query)
        count_result = list(count_job.result())
        row_count    = count_result[0]["row_count"]

        # Build column profiles from schema
        columns = []
        for field in bq_table.schema:
            precision_warning = None

            # Add warning if column type is lossy
            if is_lossy(field.name):
                precision_warning = (
                    f"Column '{field.name}' may have lost "
                    f"precision during type conversion"
                )

            columns.append(
                ColumnProfile(
                    name=field.name,
                    type=field.field_type,
                    nullable=(field.mode != "REQUIRED"),
                    precision_warning=precision_warning
                )
            )

        return TableProfile(
            sandbox_id=sandbox_id,
            table_name=table,
            row_count=row_count,
            columns=columns
        )

    # ─────────────────────────────────────────────
    # Internal Helper
    # ─────────────────────────────────────────────

    def _require_client(self) -> None:
        """
        Raise clear error if connect() was not called first.
        """
        if self.client is None:
            raise RuntimeError(
                "BigQueryAdapter not connected. "
                "Call connect(config) before using the adapter."
            )
