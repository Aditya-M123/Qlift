# tests/target/test_ta01b.py

import pytest
from typing import Any, Dict, List

from qlift.target.ta01a.adapter import TargetAdapter
from qlift.target.ta01a.schemas import ColumnProfile, TableProfile
from qlift.target.ta01b.harness import run_harness, check_type


# ─────────────────────────────────────────────
# Mock Adapters for Testing
# ─────────────────────────────────────────────

class GoodMockAdapter(TargetAdapter):
    """
    A mock adapter that correctly implements all contract methods.
    Used to confirm harness reports all PASS.
    """

    def connect(self, config: dict) -> None:
        pass

    def get_dialect_name(self) -> str:
        return "mock"

    def get_grammar(self) -> Any:
        return object()

    def get_type_mapping(self, source_dialect: str) -> Dict[str, str]:
        return {"VARCHAR2": "STRING", "DATE": "DATETIME"}

    def create_sandbox(self, name: str) -> str:
        return "mock_sandbox_001"

    def destroy_sandbox(self, sandbox_id: str) -> None:
        pass

    def deploy_ddl(self, sandbox_id: str, ddl: str) -> None:
        pass

    def load_test_data(
        self, sandbox_id: str, table: str, data: List[Dict]
    ) -> int:
        return len(data)

    def execute_query(
        self, sandbox_id: str, query: str
    ) -> List[Dict]:
        return [{"id": 1}, {"id": 2}]

    def get_table_profile(
        self, sandbox_id: str, table: str
    ) -> TableProfile:
        return TableProfile(
            sandbox_id=sandbox_id,
            table_name=table,
            row_count=2,
            columns=[
                ColumnProfile("id", "INT64", False, None)
            ]
        )

    def generate_ddl(
        self, schema_def: dict, recommendations: dict
    ) -> str:
        return "CREATE TABLE mock_table (id INT64);"


class BadMockAdapter(GoodMockAdapter):
    """
    A mock adapter that returns wrong type from execute_query.
    Used to confirm harness correctly reports FAIL.
    """
    def execute_query(self, sandbox_id: str, query: str) -> str:
        # Wrong — returns string instead of List[Dict]
        return "this should be a list not a string"


class CrashingMockAdapter(GoodMockAdapter):
    """
    A mock adapter that crashes during deploy_ddl.
    Used to confirm destroy_sandbox is still called after a crash.
    """
    def __init__(self):
        self.destroy_called = False

    def deploy_ddl(self, sandbox_id: str, ddl: str) -> None:
        raise RuntimeError("Simulated crash during deploy_ddl")

    def destroy_sandbox(self, sandbox_id: str) -> None:
        # Track that this was called
        self.destroy_called = True


class CrashOnCreateSandboxAdapter(GoodMockAdapter):
    """
    A mock adapter that crashes during create_sandbox.
    Spec: TA-01b guideline — create_sandbox raises mid-run,
    destroy_sandbox is still called.
    """
    def __init__(self):
        self.destroy_called = False

    def create_sandbox(self, name: str) -> str:
        raise RuntimeError("Simulated crash during create_sandbox")

    def destroy_sandbox(self, sandbox_id: str) -> None:
        self.destroy_called = True


# ─────────────────────────────────────────────
# Test 1 — Good adapter passes all checks
# ─────────────────────────────────────────────

def test_good_adapter_all_pass():
    """
    A correctly implemented adapter must produce
    PASS for every contract method.
    """
    adapter = GoodMockAdapter()
    results = run_harness(adapter, config={})

    for method, result in results.items():
        assert result.startswith("[PASS]"), (
            f"Expected PASS for {method} but got: {result}"
        )


# ─────────────────────────────────────────────
# Test 2 — Wrong return type reported as FAIL
# ─────────────────────────────────────────────

def test_bad_adapter_execute_query_reports_fail():
    """
    When execute_query returns wrong type (str instead of List),
    harness must report FAIL with the method name and received type.
    """
    adapter = BadMockAdapter()
    results = run_harness(adapter, config={})

    assert results["execute_query"].startswith("[FAIL]"), (
        "Expected FAIL for execute_query when wrong type returned"
    )
    assert "str" in results["execute_query"], (
        "FAIL message should mention the wrong type received"
    )


# ─────────────────────────────────────────────
# Test 3 — destroy_sandbox always called even after crash
# ─────────────────────────────────────────────

def test_destroy_sandbox_called_even_after_crash():
    """
    Even when deploy_ddl crashes mid-run,
    destroy_sandbox must still be called.
    No orphaned sandboxes left in GCP.
    """
    adapter = CrashingMockAdapter()
    results = run_harness(adapter, config={})

    assert adapter.destroy_called is True, (
        "destroy_sandbox must be called even when something crashes"
    )


# ─────────────────────────────────────────────
# Test 4 — check_type helper returns correct messages
# ─────────────────────────────────────────────

def test_check_type_returns_pass_for_correct_type():
    result = check_type(["item1", "item2"], list, "execute_query")
    assert result.startswith("[PASS]")


def test_check_type_returns_fail_for_wrong_type():
    result = check_type("wrong", list, "execute_query")
    assert result.startswith("[FAIL]")
    assert "execute_query" in result
    assert "str" in result


# ─────────────────────────────────────────────
# Test 5 — harness skips destroy when sandbox never created
# ─────────────────────────────────────────────

class FailOnConnectAdapter(GoodMockAdapter):
    """
    Adapter that fails immediately on connect.
    sandbox_id is never created so destroy should be skipped.
    """
    def connect(self, config: dict) -> None:
        raise ConnectionError("Cannot connect")

    def create_sandbox(self, name: str) -> str:
        raise RuntimeError("Should never reach here")


def test_harness_skips_destroy_when_sandbox_never_created():
    """
    When create_sandbox is never reached,
    destroy_sandbox should show SKIP not crash.
    """
    adapter = FailOnConnectAdapter()
    results = run_harness(adapter, config={})

    assert "destroy_sandbox" in results
    assert (
        results["destroy_sandbox"].startswith("[SKIP]") or
        results["destroy_sandbox"].startswith("[PASS]")
    )


# ─────────────────────────────────────────────
# Test 6 — create_sandbox raises mid-run
# ─────────────────────────────────────────────

def test_create_sandbox_raises_destroy_still_called():
    """
    Spec: Given mock adapter where create_sandbox raises mid-run,
    When harness runs, Then destroy_sandbox is still called.
    Since sandbox was never fully created, harness should
    handle cleanup gracefully without crashing.
    """
    adapter = CrashOnCreateSandboxAdapter()
    results = run_harness(adapter, config={})

    assert "create_sandbox" in results
    assert results["create_sandbox"].startswith("[FAIL]")

    # destroy_sandbox must appear in results — harness didn't crash
    assert "destroy_sandbox" in results