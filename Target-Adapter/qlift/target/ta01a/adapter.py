# qlift/target/ta01a/adapter.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from qlift.target.ta01a.schemas import TableProfile


class TargetAdapter(ABC):
    """
    Abstract contract that every target database adapter must follow.

    This is the rulebook. It cannot be used directly.
    Only concrete adapters like BigQueryAdapter can be used.

    The Verify service only ever imports and talks to this class.
    It never knows whether BigQuery, AlloyDB, or Spanner is behind it.
    """

    @abstractmethod
    def connect(self, config: dict) -> None:
        """
        Log into the target database.

        Args:
            config: connection details as a dict
                    e.g. {"project_id": "my-gcp-project"}

        Returns:
            None
        """
        pass

    @abstractmethod
    def get_dialect_name(self) -> str:
        """
        Return the name of this target dialect.

        Returns:
            str: e.g. "bigquery", "alloydb", "spanner"
        """
        pass

    @abstractmethod
    def get_grammar(self) -> Any:
        """
        Return the SQL grammar rules for this target database.
        Used by the symbolic validator to check translated SQL.

        Returns:
            Grammar object specific to this target database
        """
        pass

    @abstractmethod
    def get_type_mapping(self, source_dialect: str) -> Dict[str, str]:
        """
        Return the type conversion table from source to target.

        Args:
            source_dialect: name of the source database
                            e.g. "oracle", "sqlserver", "mysql"

        Returns:
            Dict mapping source types to target types
            e.g. {
                "VARCHAR2": "STRING",
                "DATE": "DATETIME",
                "NUMBER": "NUMERIC"
            }
        """
        pass

    @abstractmethod
    def create_sandbox(self, name: str) -> str:
        """
        Create a temporary isolated space for testing translations.
        This space is created fresh for every verification run.

        Args:
            name: a human readable label for this sandbox
                  e.g. "orders_migration_test"

        Returns:
            str: unique sandbox id
                 e.g. "qlift_sandbox_abc123"
        """
        pass

    @abstractmethod
    def destroy_sandbox(self, sandbox_id: str) -> None:
        """
        Permanently delete the sandbox and everything inside it.
        Must always be called after testing — even if tests fail.

        Args:
            sandbox_id: the id returned by create_sandbox()

        Returns:
            None
        """
        pass

    @abstractmethod
    def deploy_ddl(self, sandbox_id: str, ddl: str) -> None:
        """
        Run DDL statements inside the sandbox.
        e.g. CREATE TABLE, CREATE VIEW

        Args:
            sandbox_id: which sandbox to deploy into
            ddl: SQL DDL string to execute

        Returns:
            None
        """
        pass

    @abstractmethod
    def load_test_data(
        self,
        sandbox_id: str,
        table: str,
        data: List[Dict]
    ) -> int:
        """
        Insert test rows into a sandbox table.

        Args:
            sandbox_id: which sandbox to load into
            table: table name to insert rows into
            data: list of rows as dicts
                  e.g. [
                      {"order_id": 1, "amount": 99.99},
                      {"order_id": 2, "amount": 150.00}
                  ]

        Returns:
            int: number of rows successfully inserted
        """
        pass

    @abstractmethod
    def execute_query(
        self,
        sandbox_id: str,
        query: str
    ) -> List[Dict]:
        """
        Run a SQL query inside the sandbox and return results.

        Args:
            sandbox_id: which sandbox to query
            query: SQL string to execute

        Returns:
            List[Dict]: list of rows, each row is a dict
                        e.g. [
                            {"order_id": 1, "amount": 99.99},
                            {"order_id": 2, "amount": 150.00}
                        ]
        """
        pass

    @abstractmethod
    def get_table_profile(
        self,
        sandbox_id: str,
        table: str
    ) -> TableProfile:
        """
        Collect statistical profile of a sandbox table.
        Runs row counts, min, max, avg, null counts per column.

        Args:
            sandbox_id: which sandbox to profile
            table: table name to collect statistics on

        Returns:
            TableProfile: statistics about the table and its columns
        """
        pass

    @abstractmethod
    def generate_ddl(
        self,
        schema_def: dict,
        recommendations: dict
    ) -> str:
        """
        Generate a CREATE TABLE statement for the target database.
        Includes PARTITION BY and CLUSTER BY from recommendations.

        Args:
            schema_def: table definition as dict
                        e.g. {
                            "table_name": "orders",
                            "dataset": "sales",
                            "columns": [...]
                        }
            recommendations: partition and cluster suggestions
                        e.g. {
                            "partition_column": "order_date",
                            "cluster_columns": ["customer_id"]
                        }

        Returns:
            str: complete CREATE TABLE SQL string
        """
        pass
